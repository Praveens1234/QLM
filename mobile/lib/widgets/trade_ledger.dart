import 'dart:io';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:share_plus/share_plus.dart';
import 'package:path_provider/path_provider.dart';

/// Trade ledger list for backtest results — optimized for mobile.
class TradeLedger extends StatefulWidget {
  final List<Map<String, dynamic>> trades;

  const TradeLedger({super.key, required this.trades});

  @override
  State<TradeLedger> createState() => _TradeLedgerState();
}

class _TradeLedgerState extends State<TradeLedger> {
  String _searchQuery = '';
  String _filterType = 'All'; // All, Winners, Losers, Long, Short

  List<Map<String, dynamic>> get _filteredTrades {
    return widget.trades.where((t) {
      final pnl = (t['pnl'] as num?)?.toDouble() ?? 0;
      final dir = t['direction']?.toString() ?? '';
      
      // Filter Type
      if (_filterType == 'Winners' && pnl <= 0) return false;
      if (_filterType == 'Losers' && pnl > 0) return false;
      if (_filterType == 'Long' && dir != 'long') return false;
      if (_filterType == 'Short' && dir != 'short') return false;

      // Search Query
      if (_searchQuery.isNotEmpty) {
        final q = _searchQuery.toLowerCase();
        final reason = t['exit_reason']?.toString().toLowerCase() ?? '';
        final time = t['entry_time']?.toString().toLowerCase() ?? '';
        if (!reason.contains(q) && !time.contains(q) && !dir.contains(q)) {
          return false;
        }
      }
      return true;
    }).toList();
  }

  Future<void> _exportCsv() async {
    if (widget.trades.isEmpty) return;
    
    final buffer = StringBuffer();
    // Header
    final keys = widget.trades.first.keys.toList();
    buffer.writeln(keys.join(','));
    
    // Rows
    for (final t in widget.trades) {
      final row = keys.map((k) {
        final v = t[k]?.toString() ?? '';
        // Escape commas
        return v.contains(',') ? '"$v"' : v;
      }).join(',');
      buffer.writeln(row);
    }
    
    try {
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/qlm_trades_export.csv');
      await file.writeAsString(buffer.toString());
      await Share.shareXFiles([XFile(file.path)], text: 'QLM Backtest Trades');
    } catch (e) {
      debugPrint('Export failed: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (widget.trades.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            'No trades',
            style: GoogleFonts.inter(
              fontSize: 13,
              color: isDark ? const Color(0xFF475569) : const Color(0xFF94A3B8),
            ),
          ),
        ),
      );
    }

    final displayedTrades = _filteredTrades;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Controls Row
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              Text('Trades', style: GoogleFonts.inter(fontSize: 16, fontWeight: FontWeight.bold)),
              const Spacer(),
              IconButton(
                icon: const Icon(Icons.download_rounded, size: 20),
                tooltip: 'Export CSV',
                onPressed: _exportCsv,
              ),
            ],
          ),
        ),
        
        // Search & Filters
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            decoration: InputDecoration(
              hintText: 'Search time, reason...',
              prefixIcon: const Icon(Icons.search, size: 18),
              isDense: true,
              contentPadding: const EdgeInsets.all(8),
            ),
            style: GoogleFonts.inter(fontSize: 13),
            onChanged: (v) => setState(() => _searchQuery = v),
          ),
        ),
        const SizedBox(height: 8),
        SizedBox(
          height: 32,
          child: ListView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: 16),
            children: ['All', 'Winners', 'Losers', 'Long', 'Short'].map((f) {
              final isSel = _filterType == f;
              return Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(f, style: GoogleFonts.inter(fontSize: 11)),
                  selected: isSel,
                  onSelected: (val) => setState(() => _filterType = val ? f : 'All'),
                  padding: EdgeInsets.zero,
                  labelPadding: const EdgeInsets.symmetric(horizontal: 8),
                ),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 12),

        // List
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: displayedTrades.length,
          itemBuilder: (context, index) {
            final t = displayedTrades[index];
            return _TradeRow(trade: t, isDark: isDark, index: index);
          },
        ),
      ],
    );
  }
}

class _TradeRow extends StatelessWidget {
  final Map<String, dynamic> trade;
  final bool isDark;
  final int index;

  const _TradeRow({
    required this.trade,
    required this.isDark,
    required this.index,
  });

  @override
  Widget build(BuildContext context) {
    final pnl = (trade['pnl'] as num?)?.toDouble() ?? 0;
    final isWin = pnl > 0;
    final direction = trade['direction']?.toString() ?? '';
    final isLong = direction == 'long';
    final entryTime = trade['entry_time']?.toString() ?? '';
    final exitReason = trade['exit_reason']?.toString() ?? '';
    final rMultiple = (trade['r_multiple'] as num?)?.toDouble() ?? 0;
    final entryPrice = (trade['entry_price'] as num?)?.toDouble() ?? 0;
    final exitPrice = (trade['exit_price'] as num?)?.toDouble() ?? 0;
    final duration = (trade['duration'] as num?)?.toDouble() ?? 0;

    return Container(
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: isDark ? const Color(0xFF1E293B) : const Color(0xFFE2E8F0),
            width: 0.5,
          ),
        ),
      ),
      child: ExpansionTile(
        tilePadding: const EdgeInsets.symmetric(horizontal: 12),
        childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
        leading: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: isLong
                ? const Color(0xFF10B981).withOpacity(0.1)
                : const Color(0xFFF43F5E).withOpacity(0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            isLong ? Icons.trending_up : Icons.trending_down,
            size: 16,
            color: isLong ? const Color(0xFF10B981) : const Color(0xFFF43F5E),
          ),
        ),
        title: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entryTime.split(' ').first,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: isDark ? Colors.white : Colors.black87,
                    ),
                  ),
                  Text(
                    entryTime.split(' ').length > 1 ? entryTime.split(' ')[1] : '',
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      color: const Color(0xFF64748B),
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text(
                  '${isWin ? '+' : ''}\$${pnl.toStringAsFixed(2)}',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: isWin ? const Color(0xFF10B981) : const Color(0xFFF43F5E),
                  ),
                ),
                Text(
                  '${rMultiple.toStringAsFixed(2)}R',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: const Color(0xFF64748B),
                  ),
                ),
              ],
            ),
          ],
        ),
        children: [
          _detailRow('Entry Price', entryPrice.toStringAsFixed(2), isDark),
          _detailRow('Exit Price', exitPrice.toStringAsFixed(2), isDark),
          _detailRow('Duration', '${duration.toStringAsFixed(0)} min', isDark),
          _detailRow('Exit Reason', exitReason, isDark),
          if (trade['sl'] != null)
            _detailRow('Stop Loss', (trade['sl'] as num).toDouble().toStringAsFixed(2), isDark),
          if (trade['tp'] != null)
            _detailRow('Take Profit', (trade['tp'] as num).toDouble().toStringAsFixed(2), isDark),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 11,
              color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.w500,
              color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
            ),
          ),
        ],
      ),
    );
  }
}
