class Trade {
  final int id;
  final String entryTime;
  final String direction;
  final double entryPrice;
  final double exitPrice;
  final String exitTime;
  final double pnl;
  final double grossPnl;
  final double commission;
  final double rMultiple;
  final double? sl;
  final double? tp;
  final double mae;
  final double mfe;
  final double? maePrice;
  final double? mfePrice;
  final double? maePnl;
  final double? mfePnl;
  final double? maeR;
  final double? mfeR;
  final double duration;
  final String exitReason;
  final double size;
  final double initialRisk;

  Trade({
    required this.id,
    required this.entryTime,
    required this.direction,
    required this.entryPrice,
    required this.exitPrice,
    required this.exitTime,
    required this.pnl,
    this.grossPnl = 0.0,
    this.commission = 0.0,
    required this.rMultiple,
    this.sl,
    this.tp,
    this.mae = 0.0,
    this.mfe = 0.0,
    this.maePrice,
    this.mfePrice,
    this.maePnl,
    this.mfePnl,
    this.maeR,
    this.mfeR,
    this.duration = 0.0,
    this.exitReason = '',
    this.size = 1.0,
    this.initialRisk = 0.0,
  });

  bool get isWin => pnl > 0;
  bool get isLong => direction == 'long';

  factory Trade.fromJson(Map<String, dynamic> json, int index) {
    return Trade(
      id: index,
      entryTime: json['entry_time']?.toString() ?? '',
      direction: json['direction']?.toString() ?? '',
      entryPrice: (json['entry_price'] as num?)?.toDouble() ?? 0.0,
      exitPrice: (json['exit_price'] as num?)?.toDouble() ?? 0.0,
      exitTime: json['exit_time']?.toString() ?? '',
      pnl: (json['pnl'] as num?)?.toDouble() ?? 0.0,
      grossPnl: (json['gross_pnl'] as num?)?.toDouble() ?? 0.0,
      commission: (json['commission'] as num?)?.toDouble() ?? 0.0,
      rMultiple: (json['r_multiple'] as num?)?.toDouble() ?? 0.0,
      sl: (json['sl'] as num?)?.toDouble(),
      tp: (json['tp'] as num?)?.toDouble(),
      mae: (json['mae'] as num?)?.toDouble() ?? 0.0,
      mfe: (json['mfe'] as num?)?.toDouble() ?? 0.0,
      maePrice: (json['mae_price'] as num?)?.toDouble(),
      mfePrice: (json['mfe_price'] as num?)?.toDouble(),
      maePnl: (json['mae_pnl'] as num?)?.toDouble(),
      mfePnl: (json['mfe_pnl'] as num?)?.toDouble(),
      maeR: (json['mae_r'] as num?)?.toDouble(),
      mfeR: (json['mfe_r'] as num?)?.toDouble(),
      duration: (json['duration'] as num?)?.toDouble() ?? 0.0,
      exitReason: json['exit_reason']?.toString() ?? '',
      size: (json['size'] as num?)?.toDouble() ?? 1.0,
      initialRisk: (json['initial_risk'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'entry_time': entryTime,
        'direction': direction,
        'entry_price': entryPrice,
        'exit_price': exitPrice,
        'exit_time': exitTime,
        'pnl': pnl,
        'r_multiple': rMultiple,
        'sl': sl,
        'tp': tp,
        'mae': mae,
        'mfe': mfe,
        'duration': duration,
        'exit_reason': exitReason,
      };
}
