
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:file_picker/file_picker.dart';
import '../providers/data_provider.dart';
import '../widgets/glass_card.dart';
import '../widgets/toast.dart';
import '../models/dataset.dart';

class DataManagerScreen extends StatefulWidget {
  const DataManagerScreen({super.key});

  @override
  State<DataManagerScreen> createState() => _DataManagerScreenState();
}

class _DataManagerScreenState extends State<DataManagerScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _symbolController = TextEditingController();
  final _tfController = TextEditingController(text: '1m');
  final _urlController = TextEditingController();

  PlatformFile? _selectedFile;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DataProvider>().loadDatasets();
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _symbolController.dispose();
    _tfController.dispose();
    _urlController.dispose();
    super.dispose();
  }

  Future<void> _pickFile() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['csv'],
        withData: true,
      );

      if (result != null) {
        setState(() {
          _selectedFile = result.files.first;
        });
      }
    } catch (e) {
      if (mounted) AppToast.error(context, 'Failed to pick file: $e');
    }
  }

  Future<void> _uploadFile() async {
    if (_selectedFile == null || _selectedFile!.bytes == null) {
      AppToast.warning(context, 'Please select a CSV file');
      return;
    }

    final symbol = _symbolController.text.trim().toUpperCase();
    final timeframe = _tfController.text.trim().toLowerCase();

    if (symbol.isEmpty || timeframe.isEmpty) {
      AppToast.warning(context, 'Symbol and Timeframe are required');
      return;
    }

    final provider = context.read<DataProvider>();
    final success = await provider.uploadFile(
      bytes: _selectedFile!.bytes!,
      fileName: _selectedFile!.name,
      symbol: symbol,
      timeframe: timeframe,
    );

    if (success && mounted) {
      AppToast.success(context, 'Dataset uploaded successfully');
      setState(() {
        _selectedFile = null;
        _symbolController.clear();
      });
    } else if (mounted) {
      AppToast.error(context, provider.error ?? 'Upload failed');
    }
  }

  Future<void> _importUrl() async {
    final url = _urlController.text.trim();
    final symbol = _symbolController.text.trim().toUpperCase();
    final timeframe = _tfController.text.trim().toLowerCase();

    if (url.isEmpty || symbol.isEmpty || timeframe.isEmpty) {
      AppToast.warning(context, 'URL, Symbol, and Timeframe are required');
      return;
    }

    final provider = context.read<DataProvider>();
    final success = await provider.importUrl(
      url: url,
      symbol: symbol,
      timeframe: timeframe,
    );

    if (success && mounted) {
      AppToast.success(context, 'Dataset imported successfully');
      _urlController.clear();
      _symbolController.clear();
    } else if (mounted) {
      AppToast.error(context, provider.error ?? 'Import failed');
    }
  }

  Future<void> _deleteDataset(Dataset dataset) async {
    final provider = context.read<DataProvider>();
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Dataset?'),
        content: Text('Are you sure you want to delete ${dataset.symbol} (${dataset.timeframe})?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirm == true) {
      final success = await provider.deleteDataset(dataset.id);
      if (success && mounted) {
        AppToast.success(context, 'Dataset deleted');
      } else if (mounted) {
        AppToast.error(context, provider.error ?? 'Delete failed');
      }
    }
  }

  void _showAddDialog() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
          left: 16, right: 16, top: 24,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Add Dataset', style: GoogleFonts.inter(fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            TabBar(
              controller: _tabController,
              tabs: const [Tab(text: 'Local File'), Tab(text: 'URL Import')],
              labelColor: const Color(0xFF6366F1),
              unselectedLabelColor: Colors.grey,
              indicatorColor: const Color(0xFF6366F1),
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 350,
              child: TabBarView(
                controller: _tabController,
                children: [
                  _buildFileUploadTab(),
                  _buildUrlImportTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFileUploadTab() {
    return StatefulBuilder(
      builder: (context, setState) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _symbolController,
                    decoration: const InputDecoration(labelText: 'Symbol', hintText: 'EURUSD'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextField(
                    controller: _tfController,
                    decoration: const InputDecoration(labelText: 'Timeframe', hintText: '1m'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),
            GestureDetector(
              onTap: () async {
                await _pickFile();
                setState(() {});
              },
              child: Container(
                height: 100,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.grey.withOpacity(0.3), style: BorderStyle.solid),
                  borderRadius: BorderRadius.circular(12),
                  color: Colors.grey.withOpacity(0.05),
                ),
                child: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.upload_file, size: 32, color: _selectedFile != null ? Colors.green : Colors.grey),
                      const SizedBox(height: 8),
                      Text(
                        _selectedFile?.name ?? 'Tap to select CSV file',
                        style: TextStyle(color: _selectedFile != null ? Colors.green : Colors.grey),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Consumer<DataProvider>(
              builder: (context, provider, _) => ElevatedButton(
                onPressed: provider.uploading ? null : () {
                  _uploadFile().then((_) {
                    if (!provider.uploading && provider.error == null) Navigator.pop(context);
                  });
                },
                child: provider.uploading
                    ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Upload Dataset'),
              ),
            ),
          ],
        );
      }
    );
  }

  Widget _buildUrlImportTab() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _symbolController,
                decoration: const InputDecoration(labelText: 'Symbol', hintText: 'EURUSD'),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: TextField(
                controller: _tfController,
                decoration: const InputDecoration(labelText: 'Timeframe', hintText: '1m'),
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        TextField(
          controller: _urlController,
          decoration: const InputDecoration(labelText: 'Download URL', hintText: 'https://example.com/data.csv'),
        ),
        const SizedBox(height: 24),
        Consumer<DataProvider>(
          builder: (context, provider, _) => ElevatedButton(
            onPressed: provider.uploading ? null : () {
              _importUrl().then((_) {
                 if (!provider.uploading && provider.error == null) Navigator.pop(context);
              });
            },
            child: provider.uploading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2))
                : const Text('Import from URL'),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      floatingActionButton: FloatingActionButton(
        onPressed: _showAddDialog,
        backgroundColor: const Color(0xFF6366F1),
        child: const Icon(Icons.add, color: Colors.white),
      ),
      body: Consumer<DataProvider>(
        builder: (context, provider, _) {
          if (provider.loading && provider.datasets.isEmpty) {
            return const Center(child: CircularProgressIndicator());
          }

          return RefreshIndicator(
            onRefresh: () => provider.loadDatasets(),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  'Data Manager',
                  style: GoogleFonts.inter(fontSize: 24, fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 16),
                if (provider.datasets.isEmpty)
                  Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32.0),
                      child: Text('No datasets available.\nTap + to add one.', textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade500)),
                    ),
                  )
                else
                  ...provider.datasets.map((d) => _buildDatasetCard(d)),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildDatasetCard(Dataset dataset) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return GlassCard(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: const Color(0xFF6366F1).withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      dataset.symbol,
                      style: GoogleFonts.inter(fontWeight: FontWeight.bold, color: const Color(0xFF6366F1)),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.grey.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      dataset.timeframe,
                      style: GoogleFonts.inter(fontSize: 12, color: isDark ? Colors.grey[400] : Colors.grey[700]),
                    ),
                  ),
                ],
              ),
              IconButton(
                icon: const Icon(Icons.delete_outline, color: Colors.red, size: 20),
                onPressed: () => _deleteDataset(dataset),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildInfoItem(Icons.calendar_today, '${dataset.startDate.split(' ').first} to ${dataset.endDate.split(' ').first}'),
              _buildInfoItem(Icons.format_list_numbered, '${dataset.rowCount} rows'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildInfoItem(IconData icon, String text) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Row(
      children: [
        Icon(icon, size: 14, color: isDark ? Colors.grey[500] : Colors.grey[600]),
        const SizedBox(width: 4),
        Text(text, style: GoogleFonts.inter(fontSize: 12, color: isDark ? Colors.grey[400] : Colors.grey[700])),
      ],
    );
  }
}
