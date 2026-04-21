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

  String _greeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good Morning';
    if (hour < 17) return 'Good Afternoon';
    return 'Good Evening';
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
              // Greeting Header
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _greeting(),
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w500,
                            color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Dashboard',
                          style: GoogleFonts.inter(
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                            color: isDark ? Colors.white : const Color(0xFF0F172A),
                          ),
                        ),
                      ],
                    ),
                  ),
                  // Refresh button
                  IconButton(
                    onPressed: dash.loading ? null : () => dash.refresh(),
                    icon: dash.loading
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(
                            Icons.refresh_rounded,
                            color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                          ),
                  ),
                ],
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

              const SizedBox(height: 20),

              // Live Status Card
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withOpacity(0.04)
                      : Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark
                        ? Colors.white.withOpacity(0.06)
                        : const Color(0xFFE2E8F0),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: (dash.liveStatus == 'online'
                                ? AppConstants.statusOnline
                                : AppConstants.statusOffline)
                            .withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.bolt,
                        color: dash.liveStatus == 'online'
                            ? AppConstants.statusOnline
                            : AppConstants.statusOffline,
                        size: 22,
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
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            dash.liveStatus == 'online'
                                ? 'Connected & Monitoring'
                                : 'Offline — not connected',
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

              const SizedBox(height: 20),

              // Quick Actions
              Text(
                'Quick Actions',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
                ),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  _buildQuickAction(
                    context,
                    icon: Icons.upload_file,
                    label: 'Upload\nData',
                    color: const Color(0xFF6366F1),
                    onTap: () {
                      // Navigate to Data tab (index 1)
                      final shell = context.findAncestorStateOfType<State>();
                      if (shell != null) {
                        // Use bottom nav to switch to Data tab
                      }
                    },
                  ),
                  const SizedBox(width: 12),
                  _buildQuickAction(
                    context,
                    icon: Icons.candlestick_chart,
                    label: 'View\nCharts',
                    color: const Color(0xFF10B981),
                    onTap: () {},
                  ),
                  const SizedBox(width: 12),
                  _buildQuickAction(
                    context,
                    icon: Icons.rocket_launch,
                    label: 'Run\nBacktest',
                    color: const Color(0xFFF59E0B),
                    onTap: () {},
                  ),
                ],
              ),

              if (dash.error != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF43F5E).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: const Color(0xFFF43F5E).withOpacity(0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded,
                          color: Color(0xFFF43F5E), size: 18),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          dash.error!,
                          style: GoogleFonts.inter(
                            fontSize: 12,
                            color: const Color(0xFFF43F5E),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        );
      },
    );
  }

  Widget _buildQuickAction(
    BuildContext context, {
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 18),
          decoration: BoxDecoration(
            color: isDark
                ? color.withOpacity(0.08)
                : color.withOpacity(0.06),
            borderRadius: BorderRadius.circular(14),
            border: Border.all(
              color: color.withOpacity(0.15),
            ),
          ),
          child: Column(
            children: [
              Icon(icon, color: color, size: 26),
              const SizedBox(height: 8),
              Text(
                label,
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: isDark ? const Color(0xFFCBD5E1) : const Color(0xFF475569),
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
