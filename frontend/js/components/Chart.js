export class Chart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.chart = null;
        this.series = [];
        this.resizeObserver = null;
    }

    init() {
        if (!this.container) return;

        // Dynamic height based on viewport
        const isMobile = window.innerWidth < 768;
        const height = isMobile ? 220 : 300;

        this.chart = LightweightCharts.createChart(this.container, {
            width: this.container.clientWidth,
            height: height,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#94a3b8',
                fontSize: isMobile ? 10 : 11,
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.03)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.03)' },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Magnet,
                vertLine: {
                    color: 'rgba(148, 163, 184, 0.3)',
                    style: LightweightCharts.LineStyle.Dashed,
                    width: 1,
                },
                horzLine: {
                    color: 'rgba(148, 163, 184, 0.3)',
                    style: LightweightCharts.LineStyle.Dashed,
                    width: 1,
                },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.06)',
                minimumWidth: isMobile ? 50 : 60,
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.06)',
                timeVisible: true,
                secondsVisible: false,
            },
        });

        // Resize handling
        this.resizeObserver = new ResizeObserver(entries => {
            if (entries.length === 0 || !entries[0].contentRect) return;
            const { width } = entries[0].contentRect;
            // Maintain dynamic height on resize
            const newHeight = window.innerWidth < 768 ? 220 : 300;
            this.chart.applyOptions({ width, height: newHeight });
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

    addAreaSeries(data, color = '#6366f1') {
        if (!this.chart) this.init();

        // Clear previous area series to prevent stacking
        this.series.forEach(s => {
            try { this.chart.removeSeries(s); } catch (e) { /* ok */ }
        });
        this.series = [];

        const series = this.chart.addAreaSeries({
            lineColor: color,
            topColor: 'rgba(99, 102, 241, 0.25)',
            bottomColor: 'rgba(99, 102, 241, 0.02)',
            lineWidth: 2,
            crosshairMarkerVisible: true,
            crosshairMarkerRadius: 4,
            crosshairMarkerBorderColor: '#fff',
            crosshairMarkerBackgroundColor: color,
        });
        series.setData(data);
        this.series.push(series);

        // Fit content after setting data
        this.chart.timeScale().fitContent();

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
            this.resizeObserver = null;
        }
        this.series = [];
    }
}
