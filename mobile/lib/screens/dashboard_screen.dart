import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/dashboard_provider.dart';
import '../widgets/stat_card.dart';
import '../core/constants.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DashboardProvider>().refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Consumer<DashboardProvider>(
      builder: (context, dash, _) {
        return RefreshIndicator(
          onRefresh: () => dash.refresh(),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              // Header
              Text(
                'Dashboard',
                style: GoogleFonts.inter(
                  fontSize: 24,
                  fontWeight: FontWeight.w800,
                  color: isDark ? Colors.white : Colors.black87,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                'System Overview',
                style: GoogleFonts.inter(
                  fontSize: 13,
                  color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                ),
              ),
              const SizedBox(height: 20),

              // Stats Grid
              GridView.count(
                crossAxisCount: 2,
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
                childAspectRatio: 1.4,
                children: [
                  StatCard(
                    icon: Icons.storage,
                    iconColor: const Color(0xFF6366F1),
                    label: 'DATASETS',
                    value: dash.datasetCount.toString(),
                  ),
                  StatCard(
                    icon: Icons.code,
                    iconColor: const Color(0xFF10B981),
                    label: 'STRATEGIES',
                    value: dash.strategyCount.toString(),
                  ),
                  StatCard(
                    icon: Icons.receipt_long,
                    iconColor: const Color(0xFFF59E0B),
                    label: 'ACTIVE ORDERS',
                    value: dash.activeOrders.toString(),
                  ),
                  StatCard(
                    icon: Icons.account_balance_wallet,
                    iconColor: dash.totalPnl >= 0
                        ? AppConstants.chartGreen
                        : AppConstants.chartRed,
                    label: 'TOTAL PNL',
                    value: '\$${dash.totalPnl.toStringAsFixed(2)}',
                    valueColor: dash.totalPnl >= 0
                        ? AppConstants.chartGreen
                        : AppConstants.chartRed,
                  ),
                ],
              ),

              const SizedBox(height: 24),

              // Live Status
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withOpacity(0.04)
                      : Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withOpacity(0.06)
                        : const Color(0xFFE2E8F0),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 40,
                      height: 40,
                      decoration: BoxDecoration(
                        color: (dash.liveStatus == 'online'
                                ? AppConstants.statusOnline
                                : AppConstants.statusOffline)
                            .withOpacity(0.1),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Icon(
                        Icons.bolt,
                        color: dash.liveStatus == 'online'
                            ? AppConstants.statusOnline
                            : AppConstants.statusOffline,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Live Engine',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: isDark ? Colors.white : Colors.black87,
                            ),
                          ),
                          Text(
                            dash.liveStatus == 'online'
                                ? 'Connected & Monitoring'
                                : 'Offline',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: const Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: dash.liveStatus == 'online'
                            ? AppConstants.statusOnline
                            : AppConstants.statusOffline,
                        boxShadow: [
                          if (dash.liveStatus == 'online')
                            BoxShadow(
                              color: AppConstants.statusOnline.withOpacity(0.5),
                              blurRadius: 10,
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              if (dash.error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF43F5E).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    dash.error!,
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: const Color(0xFFF43F5E),
                    ),
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }
}
