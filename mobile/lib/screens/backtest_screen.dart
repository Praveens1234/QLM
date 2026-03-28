import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/backtest_provider.dart';
import '../providers/data_provider.dart';
import '../providers/strategy_provider.dart';
import '../models/backtest.dart';
import '../widgets/glass_card.dart';
import '../widgets/metrics_grid.dart';
import '../widgets/trade_ledger.dart';

class BacktestScreen extends StatefulWidget {
  const BacktestScreen({super.key});

  @override
  State<BacktestScreen> createState() => _BacktestScreenState();
}

class _BacktestScreenState extends State<BacktestScreen> {
  String? _datasetId;
  String? _strategyName;
  final _capitalCtrl = TextEditingController(text: '10000');
  
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DataProvider>().loadDatasets();
      context.read<StrategyProvider>().loadStrategies();
    });
  }

  void _runBacktest() {
    if (_datasetId == null || _strategyName == null) return;
    
    final req = BacktestRequest(
      datasetId: _datasetId!,
      strategyName: _strategyName!,
      initialCapital: double.tryParse(_capitalCtrl.text) ?? 10000.0,
      mode: 'capital',
    );
    
    context.read<BacktestProvider>().runBacktest(req);
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildConfigCard(),
          const SizedBox(height: 16),
          _buildProgressOrResults(),
        ],
      ),
    );
  }

  Widget _buildConfigCard() {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Backtest Configuration', style: GoogleFonts.inter(fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          
          Consumer<DataProvider>(
            builder: (context, dataProv, _) => DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Dataset'),
              value: _datasetId,
              items: dataProv.datasets.map((d) => DropdownMenuItem(value: d.id, child: Text('${d.symbol} (${d.timeframe})'))).toList(),
              onChanged: (v) => setState(() => _datasetId = v),
            ),
          ),
          const SizedBox(height: 12),
          
          Consumer<StrategyProvider>(
            builder: (context, stratProv, _) => DropdownButtonFormField<String>(
              decoration: const InputDecoration(labelText: 'Strategy'),
              value: _strategyName,
              items: stratProv.strategies.map((s) => DropdownMenuItem(value: s.name, child: Text(s.name))).toList(),
              onChanged: (v) => setState(() => _strategyName = v),
            ),
          ),
          const SizedBox(height: 12),
          
          TextField(
            controller: _capitalCtrl,
            decoration: const InputDecoration(labelText: 'Initial Capital'),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 24),
          
          Consumer<BacktestProvider>(
            builder: (context, btProv, _) => ElevatedButton(
              onPressed: (_datasetId != null && _strategyName != null && btProv.status != BacktestStatus.running) 
                  ? _runBacktest 
                  : null,
              style: ElevatedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 16)),
              child: btProv.status == BacktestStatus.running
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Text('RUN BACKTEST'),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildProgressOrResults() {
    return Consumer<BacktestProvider>(
      builder: (context, prov, _) {
        if (prov.status == BacktestStatus.idle) return const SizedBox.shrink();

        if (prov.status == BacktestStatus.running) {
          return GlassCard(
            child: Column(
              children: [
                LinearProgressIndicator(value: prov.progress / 100),
                const SizedBox(height: 16),
                Text(prov.progressMessage, style: GoogleFonts.inter()),
              ],
            ),
          );
        }

        if (prov.status == BacktestStatus.failed) {
          return GlassCard(
            child: Text('Error: ${prov.error}', style: const TextStyle(color: Colors.red)),
          );
        }

        final res = prov.result;
        if (res == null) return const SizedBox.shrink();

        return Column(
          children: [
            MetricsGrid(metrics: res.metrics),
            const SizedBox(height: 16),
            TradeLedger(trades: res.trades),
          ],
        );
      },
    );
  }
}
