import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/chart_provider.dart';
import '../providers/data_provider.dart';
import '../widgets/candlestick_chart.dart';


class ChartScreen extends StatefulWidget {
  const ChartScreen({super.key});

  @override
  State<ChartScreen> createState() => _ChartScreenState();
}

class _ChartScreenState extends State<ChartScreen> {
  String? _selectedDatasetId;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DataProvider>().loadDatasets();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Column(
      children: [
        // Controls Row
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          color: isDark ? const Color(0xFF1E293B) : Colors.white,
          child: Row(
            children: [
              // Dataset Selector
              Expanded(
                child: Consumer<DataProvider>(
                  builder: (context, dataProv, _) {
                    return DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        isExpanded: true,
                        value: _selectedDatasetId,
                        hint: const Text('Select Dataset'),
                        items: dataProv.datasets.map((d) {
                          return DropdownMenuItem(
                            value: d.id,
                            child: Text(
                              '${d.symbol} (${d.timeframe})',
                              style: GoogleFonts.inter(fontWeight: FontWeight.w600),
                            ),
                          );
                        }).toList(),
                        onChanged: (val) {
                          if (val != null) {
                            setState(() => _selectedDatasetId = val);
                            context.read<ChartProvider>().loadDataset(val);
                          }
                        },
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(width: 8),
              
              // Timeframe Selector
              Consumer<ChartProvider>(
                builder: (context, chartProv, _) {
                  if (chartProv.meta == null || _selectedDatasetId == null) return const SizedBox();
                  
                  return DropdownButtonHideUnderline(
                    child: DropdownButton<int>(
                      value: chartProv.currentTfSec,
                      items: chartProv.meta!.validTimeframes.map((tf) {
                        return DropdownMenuItem(
                          value: tf.sec,
                          child: Text(tf.label, style: GoogleFonts.inter()),
                        );
                      }).toList(),
                      onChanged: (val) {
                        if (val != null) {
                          chartProv.switchTimeframe(_selectedDatasetId!, val);
                        }
                      },
                    ),
                  );
                },
              ),

              // Indicators Menu
              Consumer<ChartProvider>(
                builder: (context, chartProv, _) {
                  return PopupMenuButton<String>(
                    icon: const Icon(Icons.show_chart),
                    itemBuilder: (context) => [
                      CheckedPopupMenuItem(value: 'sma50', checked: chartProv.showSma50, child: const Text('SMA 50')),
                      CheckedPopupMenuItem(value: 'ema20', checked: chartProv.showEma20, child: const Text('EMA 20')),
                      CheckedPopupMenuItem(value: 'ema50', checked: chartProv.showEma50, child: const Text('EMA 50')),
                      CheckedPopupMenuItem(value: 'ema200', checked: chartProv.showEma200, child: const Text('EMA 200')),
                      CheckedPopupMenuItem(value: 'bb', checked: chartProv.showBb, child: const Text('Bollinger Bands')),
                      CheckedPopupMenuItem(value: 'rsi', checked: chartProv.showRsi, child: const Text('RSI')),
                    ],
                    onSelected: (val) {
                      chartProv.toggleIndicator(val);
                    },
                  );
                }
              ),
            ],
          ),
        ),

        // Chart Area
        Expanded(
          child: Consumer<ChartProvider>(
            builder: (context, chartProv, _) {
              if (chartProv.loading && chartProv.bars.isEmpty) {
                return const Center(child: CircularProgressIndicator());
              }
              
              return CandlestickChart(
                bars: chartProv.bars,
                symbol: chartProv.meta?.symbol ?? '',
                sma50: chartProv.showSma50 ? chartProv.calculateSMA(50) : [],
                ema20: chartProv.showEma20 ? chartProv.calculateEMA(20) : [],
                ema50: chartProv.showEma50 ? chartProv.calculateEMA(50) : [],
                ema200: chartProv.showEma200 ? chartProv.calculateEMA(200) : [],
                bollingerBands: chartProv.showBb ? chartProv.calculateBollingerBands() : {},
                rsi: chartProv.showRsi ? chartProv.calculateRSI() : [],
              );
            },
          ),
        ),
      ],
    );
  }
}
