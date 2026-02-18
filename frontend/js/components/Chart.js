export class Chart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.series = [];
        this.resizeObserver = null;
    }

    init() {
        if (!this.container) return;

        this.chart = LightweightCharts.createChart(this.container, {
            width: this.container.clientWidth,
            height: 300, // Fixed height or dynamic?
            layout: {
                background: { type: 'solid', color: '#0f172a' }, // Surface color
                textColor: '#94a3b8',
            },
            grid: {
                vertLines: { color: '#1e293b' },
                horzLines: { color: '#1e293b' },
            },
            timeScale: {
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Resize handling
        this.resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || !entries[0].contentRect) return;
            const { width, height } = entries[0].contentRect;
            this.chart.applyOptions({ width, height });
        });
        this.resizeObserver.observe(this.container);
    }

    addCandleSeries(data) {
        if (!this.chart) this.init();
        const series = this.chart.addCandlestickSeries({
            upColor: '#10b981',
            downColor: '#f43f5e',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#f43f5e',
        });
        series.setData(data);
        this.series.push(series);
        return series;
    }

    addAreaSeries(data, color = '#4f46e5') {
        if (!this.chart) this.init();
        const series = this.chart.addAreaSeries({
            lineColor: color,
            topColor: color, // with opacity handled by lib
            bottomColor: 'rgba(79, 70, 229, 0.05)',
        });
        series.setData(data);
        this.series.push(series);
        return series;
    }

    setMarkers(seriesIndex, markers) {
        if (this.series[seriesIndex]) {
            this.series[seriesIndex].setMarkers(markers);
        }
    }

    destroy() {
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
    }
}
