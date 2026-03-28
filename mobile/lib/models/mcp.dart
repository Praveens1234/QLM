class McpStatus {
  final bool isActive;
  final List<McpLogEntry> logs;

  McpStatus({required this.isActive, required this.logs});

  factory McpStatus.fromJson(Map<String, dynamic> json) {
    final logList = (json['logs'] as List<dynamic>?)
            ?.map((e) => McpLogEntry.fromJson(Map<String, dynamic>.from(e as Map)))
            .toList() ??
        [];
    return McpStatus(
      isActive: json['is_active'] == true,
      logs: logList,
    );
  }
}

class McpLogEntry {
  final String timestamp;
  final String action;
  final String status;
  final dynamic details;

  McpLogEntry({
    required this.timestamp,
    required this.action,
    required this.status,
    this.details,
  });

  factory McpLogEntry.fromJson(Map<String, dynamic> json) {
    return McpLogEntry(
      timestamp: json['timestamp']?.toString() ?? '',
      action: json['action']?.toString() ?? '',
      status: json['status']?.toString() ?? 'INFO',
      details: json['details'],
    );
  }

  String get detailsString {
    if (details == null) return '';
    if (details is Map || details is List) {
      return details.toString();
    }
    return details.toString();
  }
}
