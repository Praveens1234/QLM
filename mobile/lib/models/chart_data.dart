class ChartBar {
  final int time; // Unix timestamp
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;

  ChartBar({
    required this.time,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });

  bool get isUp => close >= open;

  factory ChartBar.fromJson(Map<String, dynamic> json) {
    return ChartBar(
      time: (json['time'] as num?)?.toInt() ?? 0,
      open: (json['open'] as num?)?.toDouble() ?? 0.0,
      high: (json['high'] as num?)?.toDouble() ?? 0.0,
      low: (json['low'] as num?)?.toDouble() ?? 0.0,
      close: (json['close'] as num?)?.toDouble() ?? 0.0,
      volume: (json['volume'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class ChartTimeframe {
  final int sec;
  final String label;

  ChartTimeframe({required this.sec, required this.label});

  factory ChartTimeframe.fromJson(Map<String, dynamic> json) {
    return ChartTimeframe(
      sec: (json['sec'] as num?)?.toInt() ?? 60,
      label: json['label']?.toString() ?? '',
    );
  }
}

class ChartMeta {
  final String datasetId;
  final String symbol;
  final int baseTfSec;
  final String? startDate;
  final String? endDate;
  final int totalRows;
  final List<ChartTimeframe> validTimeframes;

  ChartMeta({
    required this.datasetId,
    required this.symbol,
    required this.baseTfSec,
    this.startDate,
    this.endDate,
    required this.totalRows,
    required this.validTimeframes,
  });

  factory ChartMeta.fromJson(Map<String, dynamic> json) {
    final meta = json['meta'] as Map<String, dynamic>? ?? json;
    final tfs = (meta['valid_timeframes'] as List<dynamic>?)
            ?.map((e) => ChartTimeframe.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];

    return ChartMeta(
      datasetId: meta['dataset_id']?.toString() ?? '',
      symbol: meta['symbol']?.toString() ?? '',
      baseTfSec: (meta['base_tf_sec'] as num?)?.toInt() ?? 0,
      startDate: meta['start_date']?.toString(),
      endDate: meta['end_date']?.toString(),
      totalRows: (meta['total_rows'] as num?)?.toInt() ?? 0,
      validTimeframes: tfs,
    );
  }
}
