import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../providers/data_provider.dart';
import '../providers/inspector_provider.dart';
import '../widgets/glass_card.dart';

class InspectorScreen extends StatefulWidget {
  const InspectorScreen({super.key});

  @override
  State<InspectorScreen> createState() => _InspectorScreenState();
}

class _InspectorScreenState extends State<InspectorScreen> {
  String? _selectedDatasetId;
  final TextEditingController _queryCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DataProvider>().loadDatasets();
    });
  }

  @override
  void dispose() {
    _queryCtrl.dispose();
    super.dispose();
  }

  void _inspect() {
    if (_selectedDatasetId == null || _queryCtrl.text.isEmpty) return;
    context.read<InspectorProvider>().inspect(_selectedDatasetId!, _queryCtrl.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Query Controls
          GlassCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text('Data Inspector', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold)),
                const SizedBox(height: 16),
                
                Consumer<DataProvider>(
                  builder: (context, dataProv, _) => DropdownButtonFormField<String>(
                    decoration: const InputDecoration(labelText: 'Dataset'),
                    value: _selectedDatasetId,
                    items: dataProv.datasets.map((d) => 
                        DropdownMenuItem(value: d.id, child: Text('${d.symbol} (${d.timeframe})'))
                    ).toList(),
                    onChanged: (v) => setState(() => _selectedDatasetId = v),
                  ),
                ),
                const SizedBox(height: 16),
                
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _queryCtrl,
                        decoration: const InputDecoration(
                          labelText: 'Search Query (Date or Index)',
                          hintText: 'e.g. 2023-01-01 or 54221',
                        ),
                        onSubmitted: (_) => _inspect(),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Consumer<InspectorProvider>(
                      builder: (context, prov, _) => ElevatedButton(
                        onPressed: (_selectedDatasetId != null && !prov.loading) ? _inspect : null,
                        style: ElevatedButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
                        ),
                        child: prov.loading 
                           ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                           : const Icon(Icons.search),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          
          const SizedBox(height: 24),
          
          // Results
          Consumer<InspectorProvider>(
            builder: (context, prov, _) {
              if (prov.error != null) {
                return GlassCard(child: Text('Error: ${prov.error}', style: const TextStyle(color: Colors.red)));
              }
              if (prov.results.isEmpty && !prov.loading) {
                return const SizedBox.shrink();
              }
              
              return GlassCard(
                padding: const EdgeInsets.all(0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        children: [
                          const Icon(Icons.table_chart_outlined, color: Color(0xFF6366F1)),
                          const SizedBox(width: 8),
                          Text('Window View (Center: ~${prov.targetIndex})', 
                              style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                    const Divider(height: 1),
                    SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: DataTable(
                        headingTextStyle: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 13),
                        dataTextStyle: GoogleFonts.jetBrainsMono(fontSize: 12),
                        columns: const [
                          DataColumn(label: Text('IDX')),
                          DataColumn(label: Text('DATETIME')),
                          DataColumn(label: Text('OPEN')),
                          DataColumn(label: Text('HIGH')),
                          DataColumn(label: Text('LOW')),
                          DataColumn(label: Text('CLOSE')),
                          DataColumn(label: Text('VOLUME')),
                        ],
                        rows: prov.results.map((r) {
                          final isTarget = r.index == prov.targetIndex;
                          final bg = isTarget 
                              ? WidgetStateProperty.all(const Color(0xFF6366F1).withOpacity(0.2)) 
                              : null;
                          
                          return DataRow(
                            color: bg,
                            cells: [
                              DataCell(Text(r.index.toString())),
                              DataCell(Text(r.datetime)),
                              DataCell(Text(r.open.toStringAsFixed(4))),
                              DataCell(Text(r.high.toStringAsFixed(4))),
                              DataCell(Text(r.low.toStringAsFixed(4))),
                              DataCell(Text(r.close.toStringAsFixed(4))),
                              DataCell(Text(r.volume.toStringAsFixed(1))),
                            ],
                          );
                        }).toList(),
                      ),
                    ),
                  ],
                ),
              );
            },
          ),
        ],
      ),
    );
  }
}
