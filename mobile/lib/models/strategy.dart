class Strategy {
  final String name;
  final List<int> versions;
  final int latestVersion;

  Strategy({
    required this.name,
    required this.versions,
    required this.latestVersion,
  });

  factory Strategy.fromJson(Map<String, dynamic> json) {
    final versionList = (json['versions'] as List<dynamic>?)
            ?.map((e) => (e as num).toInt())
            .toList() ??
        [];
    return Strategy(
      name: json['name']?.toString() ?? '',
      versions: versionList,
      latestVersion: (json['latest_version'] as num?)?.toInt() ?? 1,
    );
  }
}
