import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/strategy_provider.dart';
import '../widgets/glass_card.dart';
import '../widgets/code_editor.dart';
import '../widgets/toast.dart';
import '../models/strategy.dart';

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
      context.read<StrategyProvider>().loadStrategies();
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
                            onPressed: () {
                              provider.createNew();
                              _nameController.clear();
                            },
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
    showModalBottomSheet(
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

  Future<void> _validate(StrategyProvider provider) async {
    final result = await provider.validate();
    if (result != null && result['valid'] == true) {
      if (mounted) AppToast.success(context, 'Strategy syntax is valid!');
    } else {
      if (mounted) AppToast.error(context, result?['error'] ?? 'Validation failed');
    }
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
