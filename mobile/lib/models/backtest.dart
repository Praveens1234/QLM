class BacktestRequest {
  final String datasetId;
  final String strategyName;
  final int? version;
  final String mode;
  final double initialCapital;
  final double leverage;
  final String positionSizing;
  final double fixedSize;
  final double riskPerTrade;
  final String slippageMode;
  final double slippageValue;
  final double spreadValue;
  final bool entryOnNextBar;
  final bool skipWeekendTrades;
  final double transactionFees;

  BacktestRequest({
    required this.datasetId,
    required this.strategyName,
    this.version,
    this.mode = 'capital',
    this.initialCapital = 10000.0,
    this.leverage = 1.0,
    this.positionSizing = 'fixed',
    this.fixedSize = 1.0,
    this.riskPerTrade = 0.01,
    this.slippageMode = 'none',
    this.slippageValue = 0.0,
    this.spreadValue = 0.0,
    this.entryOnNextBar = false,
    this.skipWeekendTrades = true,
    this.transactionFees = 0.0,
  });

  Map<String, dynamic> toJson() => {
        'dataset_id': datasetId,
        'strategy_name': strategyName,
        if (version != null) 'version': version,
        'mode': mode,
        'initial_capital': initialCapital,
        'leverage': leverage,
        'position_sizing': positionSizing,
        'fixed_size': fixedSize,
        'risk_per_trade': riskPerTrade,
        'slippage_mode': slippageMode,
        'slippage_value': slippageValue,
        'spread_value': spreadValue,
        'entry_on_next_bar': entryOnNextBar,
        'skip_weekend_trades': skipWeekendTrades,
        'transaction_fees': transactionFees,
      };
}

class BacktestResult {
  final String status;
  final Map<String, dynamic> metrics;
  final List<Map<String, dynamic>> trades;
  final List<Map<String, dynamic>> equityCurve;
  final String? error;

  // Optimization-specific
  final Map<String, dynamic>? bestParams;
  final Map<String, dynamic>? bestMetrics;

  BacktestResult({
    required this.status,
    required this.metrics,
    required this.trades,
    this.equityCurve = const [],
    this.error,
    this.bestParams,
    this.bestMetrics,
  });

  bool get isSuccess => status == 'success';
  bool get isOptimization => bestParams != null;

  factory BacktestResult.fromJson(Map<String, dynamic> json) {
    final results = json['results'] as Map<String, dynamic>? ?? json;

    final tradesList = (results['trades'] as List<dynamic>?)
            ?.map((e) => Map<String, dynamic>.from(e as Map))
            .toList() ??
        [];

    final equityList = (results['equity_curve'] as List<dynamic>?)
            ?.map((e) => Map<String, dynamic>.from(e as Map))
            .toList() ??
        [];

    return BacktestResult(
      status: json['status']?.toString() ?? 'unknown',
      metrics: Map<String, dynamic>.from(results['metrics'] as Map? ?? {}),
      trades: tradesList,
      equityCurve: equityList,
      error: json['error']?.toString(),
      bestParams: results['best_params'] != null
          ? Map<String, dynamic>.from(results['best_params'] as Map)
          : null,
      bestMetrics: results['best_metrics'] != null
          ? Map<String, dynamic>.from(results['best_metrics'] as Map)
          : null,
    );
  }
}
