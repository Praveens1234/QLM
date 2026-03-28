import { chartService } from '../services/ChartService.js';
import { dataService } from '../services/DataService.js';
import { IndicatorEngine } from '../core/IndicatorEngine.js';

export class ChartView {
    constructor() {
        this.containerId = 'chart-container';
        this.chart = null;
        this.series = {
            main: null,
            volume: null,
            indicators: {} // EMA, SMA, BB (overlays)
        };
        this.panes = {}; // RSI, MACD (separate panes)

        // State
        this.currentDatasetId = null;
        this.currentSymbol = '';
        this.baseTfSec = 0;
        this.currentTfSec = 60; // Default 1M
        this.bars = []; // All currently loaded bars

        // Pagination state
        this.oldestCursor = null;
        this.hasMore = true;
        this.isLoading = false;

        // Mobile detection
        this.isMobile = window.innerWidth < 768;

        // Bound references for cleanup
        this._boundResize = null;
        this._boundCrosshairMove = null;
        this._indicatorDropdownOpen = false;

        this.bindEvents();
    }

    bindEvents() {
        const datasetSelect = document.getElementById('chart-dataset-select');
        if (datasetSelect) {
            datasetSelect.addEventListener('change', (e) => this.loadDataset(e.target.value));
        }

        // Indicator toggles
        document.querySelectorAll('.indicator-toggle').forEach(chk => {
            chk.addEventListener('change', () => this.applyIndicators());
        });

        // Click-based indicator toggle button (desktop)
        const btnToggle = document.getElementById('btn-toggle-indicators');
        if (btnToggle) {
            btnToggle.addEventListener('click', (e) => {
                e.stopPropagation();
                if (this.isMobile) {
                    this._openIndicatorSheet();
                } else {
                    this._toggleIndicatorDropdown();
                }
            });
        }

        // Close dropdown on outside click (desktop)
        document.addEventListener('click', (e) => {
            if (this._indicatorDropdownOpen) {
                const wrap = document.getElementById('indicator-btn-wrap');
                if (wrap && !wrap.contains(e.target)) {
                    this._closeIndicatorDropdown();
                }
            }
        });

        // Mobile indicator sheet
        const sheetBackdrop = document.getElementById('indicator-sheet-backdrop');
        if (sheetBackdrop) {
            sheetBackdrop.addEventListener('click', () => this._closeIndicatorSheet());
        }

        // Sync sheet toggles to main checkboxes
        document.querySelectorAll('.indicator-sheet-toggle').forEach(chk => {
            chk.addEventListener('change', (e) => {
                const syncId = e.target.dataset.sync;
                const mainChk = document.getElementById(syncId);
                if (mainChk) {
                    mainChk.checked = e.target.checked;
                    mainChk.dispatchEvent(new Event('change'));
                }
            });
        });

        // Track mobile state on resize
        window.addEventListener('resize', () => {
            this.isMobile = window.innerWidth < 768;
        });
    }

    // --- Indicator panel management ---

    _toggleIndicatorDropdown() {
        const dropdown = document.getElementById('indicator-dropdown');
        const chevron = document.getElementById('indicator-chevron');
        if (!dropdown) return;

        this._indicatorDropdownOpen = !this._indicatorDropdownOpen;
        if (this._indicatorDropdownOpen) {
            dropdown.classList.add('open');
            if (chevron) chevron.style.transform = 'rotate(180deg)';
        } else {
            this._closeIndicatorDropdown();
        }
    }

    _closeIndicatorDropdown() {
        const dropdown = document.getElementById('indicator-dropdown');
        const chevron = document.getElementById('indicator-chevron');
        if (dropdown) dropdown.classList.remove('open');
        if (chevron) chevron.style.transform = '';
        this._indicatorDropdownOpen = false;
    }

    _openIndicatorSheet() {
        const backdrop = document.getElementById('indicator-sheet-backdrop');
        const sheet = document.getElementById('indicator-sheet');
        if (backdrop) backdrop.classList.add('active');
        if (sheet) sheet.classList.add('active');

        // Sync states from main checkboxes to sheet
        document.querySelectorAll('.indicator-sheet-toggle').forEach(chk => {
            const syncId = chk.dataset.sync;
            const mainChk = document.getElementById(syncId);
            if (mainChk) chk.checked = mainChk.checked;
        });
    }

    _closeIndicatorSheet() {
        const backdrop = document.getElementById('indicator-sheet-backdrop');
        const sheet = document.getElementById('indicator-sheet');
        if (backdrop) backdrop.classList.remove('active');
        if (sheet) sheet.classList.remove('active');
    }

    // --- Lifecycle ---

    async mount() {
        await this.populateDatasets();
        if (!this.chart) {
            this.initChart();
        }
    }

    unmount() {
        // Clean up to prevent memory leaks
        if (this.chart) {
            this.chart.remove();
            this.chart = null;
            this.series.main = null;
            this.series.volume = null;
            this.series.indicators = {};
        }
    }

    initChart() {
        const container = document.getElementById(this.containerId);
        if (!container) return;
        container.innerHTML = '';

        const isMobile = this.isMobile;

        const chartOptions = {
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#94a3b8',
                fontSize: isMobile ? 10 : 12,
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
            },
            crosshair: {
                mode: isMobile
                    ? LightweightCharts.CrosshairMode.Magnet  // Better for touch
                    : LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    width: 1,
                    color: 'rgba(148, 163, 184, 0.3)',
                    style: LightweightCharts.LineStyle.Dashed,
                },
                horzLine: {
                    width: 1,
                    color: 'rgba(148, 163, 184, 0.3)',
                    style: LightweightCharts.LineStyle.Dashed,
                },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.08)',
                scaleMargins: { top: 0.05, bottom: 0.2 },
                minimumWidth: isMobile ? 55 : 65,
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.08)',
                timeVisible: true,
                secondsVisible: false,
                minBarSpacing: isMobile ? 3 : 5,
            },
            autoSize: true,
        };

        this.chart = LightweightCharts.createChart(container, chartOptions);

        // Main candlestick series
        this.series.main = this.chart.addCandlestickSeries({
            upColor: '#10b981',
            downColor: '#f43f5e',
            borderVisible: false,
            wickUpColor: '#10b981',
            wickDownColor: '#f43f5e',
        });

        // Volume series
        this.series.volume = this.chart.addHistogramSeries({
            color: '#4f46e5',
            priceFormat: { type: 'volume' },
            priceScaleId: '',
        });

        this.series.volume.priceScale().applyOptions({
            scaleMargins: {
                top: isMobile ? 0.88 : 0.85,
                bottom: 0,
            },
        });

        // Setup scroll-back listener for lazy loading
        this.chart.timeScale().subscribeVisibleLogicalRangeChange(
            logicalRange => this.onVisibleLogicalRangeChanged(logicalRange)
        );

        // OHLCV legend on crosshair move
        this.chart.subscribeCrosshairMove(param => this._updateLegend(param));
    }

    // --- OHLCV Legend ---

    _updateLegend(param) {
        const legendOpen = document.getElementById('legend-open');
        const legendHigh = document.getElementById('legend-high');
        const legendLow = document.getElementById('legend-low');
        const legendClose = document.getElementById('legend-close');
        const legendVol = document.getElementById('legend-vol');

        if (!legendOpen) return;

        if (!param || !param.time || !param.seriesData || !param.seriesData.size) {
            legendOpen.textContent = '\u2014';
            legendHigh.textContent = '\u2014';
            legendLow.textContent = '\u2014';
            legendClose.textContent = '\u2014';
            legendVol.textContent = '\u2014';
            return;
        }

        const candleData = param.seriesData.get(this.series.main);
        const volData = param.seriesData.get(this.series.volume);

        if (candleData) {
            const isUp = candleData.close >= candleData.open;
            const colorClass = isUp ? 'legend-up' : 'legend-down';

            const fmt = (v) => v !== undefined ? Number(v).toFixed(2) : '\u2014';
            legendOpen.textContent = fmt(candleData.open);
            legendHigh.textContent = fmt(candleData.high);
            legendLow.textContent = fmt(candleData.low);
            legendClose.textContent = fmt(candleData.close);

            // Apply color
            [legendOpen, legendHigh, legendLow, legendClose].forEach(el => {
                el.className = colorClass;
            });
        }

        if (volData && volData.value !== undefined) {
            legendVol.textContent = this._formatVolume(volData.value);
        }
    }

    _formatVolume(v) {
        if (v >= 1e9) return (v / 1e9).toFixed(1) + 'B';
        if (v >= 1e6) return (v / 1e6).toFixed(1) + 'M';
        if (v >= 1e3) return (v / 1e3).toFixed(1) + 'K';
        return v.toFixed(0);
    }

    // --- Data Loading ---

    async populateDatasets() {
        const select = document.getElementById('chart-dataset-select');
        if (!select) return;
        try {
            const datasets = await dataService.list();
            select.innerHTML = '<option value="" disabled selected>Select Dataset...</option>' +
                datasets.map(d => `<option value="${d.id}">${d.symbol} (${d.timeframe})</option>`).join('');
        } catch (e) {
            console.error(e);
        }
    }

    async loadDataset(datasetId) {
        if (!datasetId) return;
        this.currentDatasetId = datasetId;

        this.setLoading(true);
        try {
            // 1. Get Metadata & Valid Timeframes
            const metaRes = await chartService.getMeta(datasetId);
            const meta = metaRes.meta;
            this.baseTfSec = meta.base_tf_sec;

            // Extract symbol for legend
            const sel = document.getElementById('chart-dataset-select');
            if (sel) {
                const opt = sel.options[sel.selectedIndex];
                this.currentSymbol = opt ? opt.textContent.split('(')[0].trim() : '';
                const legendSymbol = document.getElementById('legend-symbol');
                if (legendSymbol) legendSymbol.textContent = this.currentSymbol;
            }

            // Render Timeframe buttons
            this.renderTimeframes(meta.valid_timeframes);

            // Set default TF
            const tf1M = meta.valid_timeframes.find(t => t.sec === 60);
            this.currentTfSec = tf1M ? 60 : meta.valid_timeframes[0].sec;
            this.updateActiveTfButton();

            // 2. Clear current data
            this.resetState();

            // 3. Load initial bars
            await this.fetchAndPrepBars();

        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to load dataset: " + e.message);
        } finally {
            this.setLoading(false);
        }
    }

    renderTimeframes(validTfs) {
        const container = document.getElementById('chart-tf-container');
        if (!container) return;

        container.innerHTML = validTfs.map(tf => `
            <button class="tf-btn bg-slate-800 text-slate-400 hover:text-white rounded-md border border-transparent"
                    data-sec="${tf.sec}">
                ${tf.label}
            </button>
        `).join('');

        container.querySelectorAll('.tf-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const sec = parseInt(e.currentTarget.dataset.sec);
                if (sec !== this.currentTfSec) {
                    this.switchTimeframe(sec);
                }
            });
        });
    }

    updateActiveTfButton() {
        document.querySelectorAll('.tf-btn').forEach(btn => {
            if (parseInt(btn.dataset.sec) === this.currentTfSec) {
                btn.classList.add('bg-indigo-600/20', 'text-indigo-400', 'border-indigo-500/50');
                btn.classList.remove('bg-slate-800', 'text-slate-400', 'border-transparent');
            } else {
                btn.classList.remove('bg-indigo-600/20', 'text-indigo-400', 'border-indigo-500/50');
                btn.classList.add('bg-slate-800', 'text-slate-400', 'border-transparent');
            }
        });
    }

    resetState() {
        this.bars = [];
        this.oldestCursor = null;
        this.hasMore = true;

        if (this.series.main) this.series.main.setData([]);
        if (this.series.volume) this.series.volume.setData([]);

        // Remove old indicator series
        Object.values(this.series.indicators).forEach(s => {
            try { this.chart.removeSeries(s); } catch (e) { /* already removed */ }
        });
        this.series.indicators = {};
    }

    async switchTimeframe(tfSeconds) {
        this.currentTfSec = tfSeconds;
        this.updateActiveTfButton();
        this.resetState();
        this.setLoading(true);
        try {
            await this.fetchAndPrepBars();
        } finally {
            this.setLoading(false);
        }
    }

    async fetchAndPrepBars() {
        if (!this.hasMore || this.isLoading || !this.currentDatasetId) return;

        this.isLoading = true;
        const loader = document.getElementById('chart-loading');
        if (loader) loader.classList.remove('hidden');

        try {
            const limit = 2000;
            const res = await chartService.getBars(this.currentDatasetId, this.currentTfSec, this.oldestCursor, limit);
            const { bars, has_more, next_cursor } = res.data;

            if (bars.length > 0) {
                // Color volume bars based on close vs open
                bars.forEach(b => {
                    b.color = b.close >= b.open ? 'rgba(16, 185, 129, 0.25)' : 'rgba(244, 63, 94, 0.25)';
                });

                // Prepend to existing
                this.bars = [...bars, ...this.bars];

                // Update chart
                this.series.main.setData(this.bars);
                this.series.volume.setData(this.bars);

                // Reapply indicators
                this.applyIndicators();
            }

            this.hasMore = has_more;
            this.oldestCursor = next_cursor;

        } catch (e) {
            console.error("Fetch bars error", e);
            if (window.Toast) window.Toast.error("Failed to fetch data: " + e.message);
        } finally {
            this.isLoading = false;
            if (loader) loader.classList.add('hidden');
        }
    }

    onVisibleLogicalRangeChanged(logicalRange) {
        if (!logicalRange) return;

        // User scrolled near the left edge (older data)
        if (logicalRange.from < 50 && this.hasMore && !this.isLoading) {
            this.fetchAndPrepBars();
        }
    }

    // --- Indicators ---

    applyIndicators() {
        if (!this.bars || this.bars.length === 0) return;

        // Clean up old indicators
        Object.values(this.series.indicators).forEach(s => {
            try { this.chart.removeSeries(s); } catch (e) { /* ok */ }
        });
        this.series.indicators = {};

        const closeData = this.bars.map(b => ({ time: b.time, close: b.close }));

        // Check toggles
        const config = {
            sma50: document.getElementById('ind-sma50')?.checked,
            ema20: document.getElementById('ind-ema20')?.checked,
            ema50: document.getElementById('ind-ema50')?.checked,
            ema200: document.getElementById('ind-ema200')?.checked,
            bb: document.getElementById('ind-bb')?.checked,
            rsi: document.getElementById('ind-rsi')?.checked,
        };

        if (config.sma50) {
            const data = IndicatorEngine.SMA(closeData, 50);
            const ls = this.chart.addLineSeries({ color: '#38bdf8', lineWidth: 1, title: 'SMA 50' });
            ls.setData(data);
            this.series.indicators.sma50 = ls;
        }

        if (config.ema20) {
            const data = IndicatorEngine.EMA(closeData, 20);
            const ls = this.chart.addLineSeries({ color: '#fcd34d', lineWidth: 1, title: 'EMA 20' });
            ls.setData(data);
            this.series.indicators.ema20 = ls;
        }

        if (config.ema50) {
            const data = IndicatorEngine.EMA(closeData, 50);
            const ls = this.chart.addLineSeries({ color: '#f472b6', lineWidth: 1.5, title: 'EMA 50' });
            ls.setData(data);
            this.series.indicators.ema50 = ls;
        }

        if (config.ema200) {
            const data = IndicatorEngine.EMA(closeData, 200);
            const ls = this.chart.addLineSeries({ color: '#a78bfa', lineWidth: 2, title: 'EMA 200' });
            ls.setData(data);
            this.series.indicators.ema200 = ls;
        }

        if (config.bb) {
            const data = IndicatorEngine.BollingerBands(closeData);
            const uLS = this.chart.addLineSeries({ color: 'rgba(56, 189, 248, 0.5)', lineWidth: 1, title: 'BB Upper' });
            const mLS = this.chart.addLineSeries({ color: 'rgba(255, 255, 255, 0.4)', lineWidth: 1, lineStyle: 1, title: 'BB Mid' });
            const lLS = this.chart.addLineSeries({ color: 'rgba(56, 189, 248, 0.5)', lineWidth: 1, title: 'BB Lower' });

            uLS.setData(data.upper);
            mLS.setData(data.middle);
            lLS.setData(data.lower);

            this.series.indicators.bbUpper = uLS;
            this.series.indicators.bbMid = mLS;
            this.series.indicators.bbLower = lLS;
        }

        if (config.rsi) {
            const data = IndicatorEngine.RSI(closeData, 14);
            const rsiSeries = this.chart.addLineSeries({
                color: '#ec4899',
                lineWidth: 1,
                title: 'RSI 14',
                priceScaleId: 'rsiPane'
            });

            this.chart.priceScale('rsiPane').applyOptions({
                scaleMargins: { top: 0.8, bottom: 0 },
                borderColor: 'rgba(255, 255, 255, 0.08)',
            });

            rsiSeries.setData(data);
            this.series.indicators.rsi = rsiSeries;
        }
    }

    setLoading(isLoading) {
        const loader = document.getElementById('chart-initial-loading');
        if (loader) {
            if (isLoading && this.bars.length === 0) {
                loader.classList.remove('hidden');
                loader.style.display = 'flex';
            } else {
                loader.classList.add('hidden');
                loader.style.display = '';
            }
        }
    }
}
