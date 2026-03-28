/**
 * Pure JS Technical Analysis Engine
 * Calculates indicators over price arrays for the frontend ChartView
 */
export class IndicatorEngine {

    /**
     * Simple Moving Average (SMA)
     * @param {Array<{time: number, close: number}>} data 
     * @param {number} period 
     */
    static SMA(data, period) {
        if (!data || data.length === 0) return [];
        const result = [];
        let sum = 0;

        for (let i = 0; i < data.length; i++) {
            sum += data[i].close;
            if (i >= period) {
                sum -= data[i - period].close;
                result.push({ time: data[i].time, value: sum / period });
            } else if (i === period - 1) {
                result.push({ time: data[i].time, value: sum / period });
            }
        }
        return result;
    }

    /**
     * Exponential Moving Average (EMA)
     */
    static EMA(data, period) {
        if (!data || data.length === 0) return [];
        const result = [];
        const multiplier = 2 / (period + 1);
        let ema = null;

        let sum = 0;
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                sum += data[i].close;
            } else if (i === period - 1) {
                sum += data[i].close;
                ema = sum / period;
                result.push({ time: data[i].time, value: ema });
            } else {
                ema = (data[i].close - ema) * multiplier + ema;
                result.push({ time: data[i].time, value: ema });
            }
        }
        return result;
    }

    /**
     * Relative Strength Index (RSI)
     */
    static RSI(data, period = 14) {
        if (!data || data.length <= period) return [];
        const result = [];

        let gains = 0;
        let losses = 0;

        // First period calculation
        for (let i = 1; i <= period; i++) {
            const diff = data[i].close - data[i - 1].close;
            if (diff >= 0) gains += diff;
            else losses -= diff;
        }

        let avgGain = gains / period;
        let avgLoss = losses / period;

        let rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
        let rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));

        result.push({ time: data[period].time, value: rsi });

        // Subsequent calculations
        for (let i = period + 1; i < data.length; i++) {
            const diff = data[i].close - data[i - 1].close;
            const gain = diff >= 0 ? diff : 0;
            const loss = diff < 0 ? -diff : 0;

            avgGain = (avgGain * (period - 1) + gain) / period;
            avgLoss = (avgLoss * (period - 1) + loss) / period;

            rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
            rsi = avgLoss === 0 ? 100 : 100 - (100 / (1 + rs));

            result.push({ time: data[i].time, value: rsi });
        }

        return result;
    }

    /**
     * MACD
     * Returns arrays for macd line, signal line, and histogram
     */
    static MACD(data, fast = 12, slow = 26, signal = 9) {
        if (!data || data.length <= slow) return { macdLine: [], signalLine: [], histogram: [] };

        const emaFast = this.EMA(data, fast);
        const emaSlow = this.EMA(data, slow);

        // Align arrays by time
        const macdLine = [];
        let slowIdx = 0;
        let fastIdx = 0;

        // Find alignment point
        while (fastIdx < emaFast.length && emaFast[fastIdx].time < emaSlow[0].time) fastIdx++;

        while (slowIdx < emaSlow.length && fastIdx < emaFast.length) {
            macdLine.push({
                time: emaSlow[slowIdx].time,
                close: emaFast[fastIdx].value - emaSlow[slowIdx].value // Use "close" key for EMA function
            });
            slowIdx++;
            fastIdx++;
        }

        // Calculate Signal Line (EMA of MACD Line)
        const signalEma = this.EMA(macdLine, signal);

        // Output format mapping
        const finalMacd = macdLine.map(m => ({ time: m.time, value: m.close }));
        const finalSignal = signalEma;
        const finalHist = [];

        // Align MACD and Signal for Histogram
        let mIdx = 0;
        let sIdx = 0;
        while (mIdx < finalMacd.length && finalMacd[mIdx].time < finalSignal[0].time) mIdx++;

        while (sIdx < finalSignal.length && mIdx < finalMacd.length) {
            finalHist.push({
                time: finalSignal[sIdx].time,
                value: finalMacd[mIdx].value - finalSignal[sIdx].value
            });
            sIdx++;
            mIdx++;
        }

        return { macdLine: finalMacd, signalLine: finalSignal, histogram: finalHist };
    }

    /**
     * Bollinger Bands
     */
    static BollingerBands(data, period = 20, stdDev = 2) {
        if (!data || data.length < period) return { upper: [], middle: [], lower: [] };

        const middle = this.SMA(data, period);
        const upper = [];
        const lower = [];

        for (let i = period - 1; i < data.length; i++) {
            const slice = data.slice(i - period + 1, i + 1);
            const mean = middle[i - period + 1].value;

            // Calculate StdDev
            let squareDiffs = 0;
            for (let j = 0; j < slice.length; j++) {
                squareDiffs += Math.pow(slice[j].close - mean, 2);
            }
            const std = Math.sqrt(squareDiffs / period);

            upper.push({ time: data[i].time, value: mean + (std * stdDev) });
            lower.push({ time: data[i].time, value: mean - (std * stdDev) });
        }

        return { upper, middle, lower };
    }
}
