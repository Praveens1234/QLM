import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/strategy_provider.dart';

import '../widgets/code_editor.dart';
import '../widgets/toast.dart';


class StrategyLabScreen extends StatefulWidget {
  const StrategyLabScreen({super.key});

  @override
  State<StrategyLabScreen> createState() => _StrategyLabScreenState();
}

class _StrategyLabScreenState extends State<StrategyLabScreen> {
  final _nameController = TextEditingController();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final p = context.read<StrategyProvider>();
      p.loadStrategies();
      p.loadTemplates();
    });
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: Row(
        children: [
          // Sidebar (Strategies List) - Hidden on small screens, can use a drawer later, 
          // but for simplicity we'll show it or make it collapsible.
          // In mobile, a side menu per screen or bottom sheet is better.
          // Let's use a bottom sheet for selecting strategy on mobile.
          Expanded(
            child: Consumer<StrategyProvider>(
              builder: (context, provider, _) {
                if (_nameController.text != provider.currentName) {
                  _nameController.text = provider.currentName;
                }
                
                return Column(
                  children: [
                    // Toolbar
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF1E293B) : Colors.white,
                        border: Border(bottom: BorderSide(color: isDark ? Colors.white.withOpacity(0.05) : Colors.grey.shade200)),
                      ),
                      child: Row(
                        children: [
                          IconButton(
                            icon: const Icon(Icons.list),
                            onPressed: () => _showStrategyList(context, provider),
                            tooltip: 'Load Strategy',
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: TextField(
                              controller: _nameController,
                              onChanged: provider.setName,
                              decoration: const InputDecoration(
                                hintText: 'Strategy Name',
                                isDense: true,
                                border: InputBorder.none,
                                enabledBorder: InputBorder.none,
                                focusedBorder: InputBorder.none,
                                filled: false,
                              ),
                              style: GoogleFonts.inter(fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.add),
                            onPressed: () => _showNewStrategySheet(context, provider),
                            tooltip: 'New Strategy',
                          ),
                          IconButton(
                            icon: const Icon(Icons.check_circle_outline),
                            onPressed: () => _validate(provider),
                            color: Colors.green,
                            tooltip: 'Validate',
                          ),
                          IconButton(
                            icon: const Icon(Icons.save),
                            onPressed: () => _save(provider),
                            color: const Color(0xFF6366F1),
                            tooltip: 'Save',
                          ),
                        ],
                      ),
                    ),
                    
                    // Editor
                    Expanded(
                      child: CodeEditorWidget(
                        code: provider.currentCode,
                        onChanged: provider.setCode,
                        readOnly: false,
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  void _showStrategyList(BuildContext context, StrategyProvider provider) {
    showModalBottomSheet<void>(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: provider.strategies.length + 1,
          itemBuilder: (context, index) {
            if (index == 0) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text('Load Strategy', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold)),
              );
            }
            final strat = provider.strategies[index - 1];
            return ListTile(
              title: Text(strat.name, style: GoogleFonts.jetBrainsMono(fontWeight: FontWeight.bold)),
              subtitle: Text('v${strat.latestVersion}'),
              trailing: IconButton(
                icon: const Icon(Icons.delete, color: Colors.red),
                onPressed: () {
                  provider.deleteStrategy(strat.name);
                  Navigator.pop(context);
                },
              ),
              onTap: () {
                provider.loadCode(strat.name, strat.latestVersion);
                Navigator.pop(context);
              },
            );
          },
        );
      },
    );
  }

  void _showNewStrategySheet(BuildContext context, StrategyProvider provider) {
    final nameCtrl = TextEditingController();
    String? selectedTemplate;

    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (context) {
        return Padding(
          padding: EdgeInsets.only(
            bottom: MediaQuery.of(context).viewInsets.bottom,
            left: 24, right: 24, top: 24,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Create New Strategy', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 16),
              
              TextField(
                controller: nameCtrl,
                decoration: const InputDecoration(
                  labelText: 'Strategy Name',
                  border: OutlineInputBorder(),
                ),
              ),
              const SizedBox(height: 16),
              
              if (provider.templates.isNotEmpty) StatefulBuilder(
                builder: (context, setStateSB) {
                  return DropdownButtonFormField<String>(
                    decoration: const InputDecoration(
                      labelText: 'Start from Template',
                      border: OutlineInputBorder(),
                    ),
                    value: selectedTemplate,
                    items: [
                      const DropdownMenuItem(value: null, child: Text('Blank Strategy')),
                      ...provider.templates.map((t) => DropdownMenuItem(value: t, child: Text(t))),
                    ],
                    onChanged: (v) => setStateSB(() => selectedTemplate = v),
                  );
                }
              ),
              const SizedBox(height: 24),
              
              ElevatedButton(
                style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
                child: const Text('CREATE'),
                onPressed: () {
                  if (nameCtrl.text.trim().isEmpty) {
                    AppToast.warning(context, 'Name required');
                    return;
                  }
                  if (selectedTemplate != null) {
                    provider.applyTemplate(selectedTemplate!);
                    provider.setName(nameCtrl.text.trim());
                  } else {
                    provider.createNew();
                    provider.setName(nameCtrl.text.trim());
                  }
                  Navigator.pop(context);
                },
              ),
              const SizedBox(height: 24),
            ],
          ),
        );
      },
    );
  }

  Future<void> _validate(StrategyProvider provider) async {
    // Show loading barrier
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );

    final result = await provider.validate();
    if (mounted) Navigator.pop(context); // Remove loading

    if (!mounted) return;

    final isValid = result != null && result['valid'] == true;
    
    showDialog<void>(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Row(
            children: [
              Icon(isValid ? Icons.check_circle : Icons.error, 
                color: isValid ? Colors.green : Colors.red),
              const SizedBox(width: 8),
              Text(isValid ? 'Validation Passed' : 'Validation Failed'),
            ],
          ),
          content: SingleChildScrollView(
            child: Text(
              (result?['error'] as String?) ?? (isValid ? 'Syntax is perfect.' : 'Unknown error'),
              style: GoogleFonts.jetBrainsMono(
                fontSize: 12,
                color: isValid ? Colors.green.shade700 : Colors.red.shade400,
              ),
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Close'),
            )
          ],
        );
      }
    );
  }

  Future<void> _save(StrategyProvider provider) async {
    if (provider.currentName.isEmpty) {
      AppToast.warning(context, 'Please enter a strategy name');
      return;
    }
    
    final success = await provider.save();
    if (success && mounted) {
      AppToast.success(context, 'Strategy saved successfully');
    } else if (mounted) {
      AppToast.error(context, provider.error ?? 'Save failed');
    }
  }
}
