class Dataset {
  final String id;
  final String symbol;
  final String timeframe;
  final String startDate;
  final String endDate;
  final int rowCount;
  final String filePath;
  final int detectedTfSec;

  Dataset({
    required this.id,
    required this.symbol,
    required this.timeframe,
    required this.startDate,
    required this.endDate,
    required this.rowCount,
    this.filePath = '',
    this.detectedTfSec = 0,
  });

  factory Dataset.fromJson(Map<String, dynamic> json) {
    return Dataset(
      id: json['id']?.toString() ?? '',
      symbol: json['symbol']?.toString() ?? '',
      timeframe: json['timeframe']?.toString() ?? '',
      startDate: json['start_date']?.toString() ?? '',
      endDate: json['end_date']?.toString() ?? '',
      rowCount: (json['row_count'] as num?)?.toInt() ?? 0,
      filePath: json['file_path']?.toString() ?? '',
      detectedTfSec: (json['detected_tf_sec'] as num?)?.toInt() ?? 0,
    );
  }
}

class Discrepancy {
  final int index;
  final String timestamp;
  final String type;
  final String details;

  Discrepancy({
    required this.index,
    required this.timestamp,
    required this.type,
    required this.details,
  });

  factory Discrepancy.fromJson(Map<String, dynamic> json) {
    return Discrepancy(
      index: (json['index'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp']?.toString() ?? '',
      type: json['type']?.toString() ?? '',
      details: json['details']?.toString() ?? '',
    );
  }
}

class DatasetRow {
  final int index;
  final String datetime;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;

  DatasetRow({
    required this.index,
    required this.datetime,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    required this.volume,
  });

  factory DatasetRow.fromJson(Map<String, dynamic> json) {
    return DatasetRow(
      index: (json['index'] as num?)?.toInt() ?? 0,
      datetime: json['datetime']?.toString() ?? '',
      open: (json['open'] as num?)?.toDouble() ?? 0.0,
      high: (json['high'] as num?)?.toDouble() ?? 0.0,
      low: (json['low'] as num?)?.toDouble() ?? 0.0,
      close: (json['close'] as num?)?.toDouble() ?? 0.0,
      volume: (json['volume'] as num?)?.toDouble() ?? 0.0,
    );
  }
}
