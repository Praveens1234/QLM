import 'package:flutter/material.dart';
import '../themes/app_theme.dart';

class DataInspectorScreen extends StatefulWidget {
  const DataInspectorScreen({super.key});

  @override
  State<DataInspectorScreen> createState() => _DataInspectorScreenState();
}

class _DataInspectorScreenState extends State<DataInspectorScreen> {
  String _searchQuery = '';
  int _currentPage = 0;
  final int _rowsPerPage = 50;

  final List<Map<String, dynamic>> _sampleData = List.generate(
    1000,
    (index) => {
      'id': index + 1,
      'timestamp': DateTime.now().subtract(Duration(days: 1000 - index)),
      'open': 100 + (index * 0.5) + (index % 7 == 0 ? -2 : 1),
      'high': 102 + (index * 0.5) + (index % 5 == 0 ? -1 : 2),
      'low': 98 + (index * 0.5) + (index % 3 == 0 ? -3 : 0.5),
      'close': 101 + (index * 0.5) + (index % 2 == 0 ? -1 : 1.5),
      'volume': 1000000 + (index * 5000),
    },
  );

  List<Map<String, dynamic>> get _filteredData {
    if (_searchQuery.isEmpty) {
      return _sampleData;
    }
    return _sampleData.where((row) {
      return row['id'].toString().contains(_searchQuery) ||
          row['close'].toString().contains(_searchQuery) ||
          row['volume'].toString().contains(_searchQuery);
    }).toList();
  }

  List<Map<String, dynamic>> get _paginatedData {
    final startIndex = _currentPage * _rowsPerPage;
    final endIndex = startIndex + _rowsPerPage;
    if (startIndex >= _filteredData.length) {
      return [];
    }
    return _filteredData.sublist(
      startIndex,
      endIndex > _filteredData.length ? _filteredData.length : endIndex,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Data Inspector'),
        actions: [
          IconButton(
            icon: const Icon(Icons.filter_list_rounded),
            onPressed: () => _showFilterDialog(context),
            tooltip: 'Filter Data',
          ),
          IconButton(
            icon: const Icon(Icons.analytics_rounded),
            onPressed: () => _showStatistics(context),
            tooltip: 'Statistics',
          ),
          IconButton(
            icon: const Icon(Icons.download_rounded),
            onPressed: () => _exportData(context),
            tooltip: 'Export',
          ),
        ],
      ),
      body: Column(
        children: [
          _buildSearchBar(context),
          const Divider(height: 1),
          _buildDataTableHeader(context),
          Expanded(
            child: _buildDataTable(context),
          ),
          _buildPaginationControls(context),
        ],
      ),
    );
  }

  Widget _buildSearchBar(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: TextField(
        decoration: InputDecoration(
          labelText: 'Search Data',
          hintText: 'Search by ID, price, volume...',
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: _searchQuery.isNotEmpty
              ? IconButton(
                  icon: const Icon(Icons.clear_rounded),
                  onPressed: () {
                    setState(() {
                      _searchQuery = '';
                    });
                  },
                )
              : null,
        ),
        onChanged: (value) {
          setState(() {
            _searchQuery = value;
            _currentPage = 0;
          });
        },
      ),
    );
  }

  Widget _buildDataTableHeader(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        children: [
          Expanded(flex: 1, child: _buildHeaderCell(context, 'ID')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'Date')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'Open')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'High')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'Low')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'Close')),
          Expanded(flex: 2, child: _buildHeaderCell(context, 'Volume')),
        ],
      ),
    );
  }

  Widget _buildHeaderCell(BuildContext context, String text) {
    return Text(
      text,
      style: Theme.of(context).textTheme.labelMedium?.copyWith(
            fontWeight: FontWeight.bold,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
    );
  }

  Widget _buildDataTable(BuildContext context) {
    if (_filteredData.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.search_off_rounded,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(height: 16),
            Text(
              'No data found',
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SizedBox(
        width: MediaQuery.of(context).size.width * 1.5,
        child: ListView.builder(
          itemCount: _paginatedData.length,
          itemBuilder: (context, index) {
            final row = _paginatedData[index];
            return _buildDataRow(context, row, index);
          },
        ),
      ),
    );
  }

  Widget _buildDataRow(BuildContext context, Map<String, dynamic> row, int index) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        children: [
          Expanded(flex: 1, child: _buildDataCell(context, row['id'].toString())),
          Expanded(flex: 2, child: _buildDataCell(context, _formatDate(row['timestamp']))),
          Expanded(flex: 2, child: _buildDataCell(context, '\$${row['open'].toStringAsFixed(2)}')),
          Expanded(flex: 2, child: _buildDataCell(context, '\$${row['high'].toStringAsFixed(2)}')),
          Expanded(flex: 2, child: _buildDataCell(context, '\$${row['low'].toStringAsFixed(2)}')),
          Expanded(
            flex: 2,
            child: _buildDataCell(
              context,
              '\$${row['close'].toStringAsFixed(2)}',
              color: _getPriceColor(row),
              fontWeight: FontWeight.bold,
            ),
          ),
          Expanded(flex: 2, child: _buildDataCell(context, _formatVolume(row['volume']))),
        ],
      ),
    );
  }

  Widget _buildDataCell(
    BuildContext context,
    String text, {
    Color? color,
    FontWeight? fontWeight,
  }) {
    return Text(
      text,
      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: color ?? Theme.of(context).colorScheme.onSurface,
            fontWeight: fontWeight,
          ),
      overflow: TextOverflow.ellipsis,
    );
  }

  Widget _buildPaginationControls(BuildContext context) {
    final totalPages = (_filteredData.length / _rowsPerPage).ceil();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            'Page ${_currentPage + 1} of ${totalPages > 0 ? totalPages : 1}',
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
          Row(
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left_rounded),
                onPressed: _currentPage > 0
                    ? () {
                        setState(() {
                          _currentPage--;
                        });
                      }
                    : null,
              ),
              Text('${(_currentPage * _rowsPerPage) + 1}-${
                    (_currentPage * _rowsPerPage) + _paginatedData.length
                  } of ${_filteredData.length}'),
              IconButton(
                icon: const Icon(Icons.chevron_right_rounded),
                onPressed: _currentPage < totalPages - 1
                    ? () {
                        setState(() {
                          _currentPage++;
                        });
                      }
                    : null,
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDate(DateTime date) {
    return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
  }

  String _formatVolume(double volume) {
    if (volume >= 1000000) {
      return '\$${(volume / 1000000).toStringAsFixed(1)}M';
    }
    if (volume >= 1000) {
      return '\$${(volume / 1000).toStringAsFixed(1)}K';
    }
    return '\$${volume.toStringAsFixed(0)}';
  }

  Color _getPriceColor(Map<String, dynamic> row) {
    final close = row['close'] as double;
    final open = row['open'] as double;
    return close >= open ? Colors.green : Colors.red;
  }

  void _showFilterDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Filter Data'),
        content: const Text('Advanced filtering options coming soon'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showStatistics(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Data Statistics'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildStatRow(context, 'Total Rows', '1,000'),
              _buildStatRow(context, 'Date Range', '2022-01-01 to 2024-12-31'),
              _buildStatRow(context, 'Avg Close Price', '\$123.45'),
              _buildStatRow(context, 'Avg Volume', '1.2M'),
              _buildStatRow(context, 'Missing Values', '0'),
              _buildStatRow(context, 'Data Quality', '99.8%'),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _buildStatRow(BuildContext context, String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label),
          Text(
            value,
            style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
          ),
        ],
      ),
    );
  }

  void _exportData(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Exporting data...')),
    );
  }
}