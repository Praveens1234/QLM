import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/server_provider.dart';
import 'dashboard_screen.dart';
import 'data_manager_screen.dart';
import 'chart_screen.dart';
import 'backtest_screen.dart';
import 'strategy_lab_screen.dart';
import 'inspector_screen.dart';
import 'mcp_screen.dart';
import 'settings_screen.dart';

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _selectedIndex = 0;

  // Primary nav screens + "More" sub-screens
  static const _primaryScreens = [
    DashboardScreen(),
    DataManagerScreen(),
    ChartScreen(),
    BacktestScreen(),
  ];

  // More menu screens
  void _openMoreMenu() {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: isDark ? const Color(0xFF1E293B) : Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Handle bar
              Container(
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF475569) : const Color(0xFFCBD5E1),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'More',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : Colors.black87,
                ),
              ),
              const SizedBox(height: 16),
              _moreItem(
                icon: Icons.code,
                label: 'Strategy Lab',
                color: const Color(0xFF6366F1),
                onTap: () => _navigateToMore(const StrategyLabScreen()),
              ),
              _moreItem(
                icon: Icons.search,
                label: 'Data Inspector',
                color: const Color(0xFF06B6D4),
                onTap: () => _navigateToMore(const InspectorScreen()),
              ),
              _moreItem(
                icon: Icons.hub,
                label: 'MCP Service',
                color: const Color(0xFF8B5CF6),
                onTap: () => _navigateToMore(const McpScreen()),
              ),
              _moreItem(
                icon: Icons.settings,
                label: 'Settings',
                color: const Color(0xFF64748B),
                onTap: () => _navigateToMore(const SettingsScreen()),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _moreItem({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return ListTile(
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: color.withOpacity(0.1),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Icon(icon, color: color, size: 20),
      ),
      title: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: isDark ? Colors.white : Colors.black87,
        ),
      ),
      trailing: Icon(
        Icons.chevron_right,
        size: 20,
        color: isDark ? const Color(0xFF475569) : const Color(0xFFCBD5E1),
      ),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      onTap: onTap,
    );
  }

  void _navigateToMore(Widget screen) {
    Navigator.of(context).pop(); // Close sheet
    Navigator.of(context).push(
      MaterialPageRoute<void>(builder: (_) => screen),
    );
  }

  @override
  Widget build(BuildContext context) {

    final server = context.watch<ServerProvider>();

    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                color: const Color(0xFF6366F1).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.candlestick_chart,
                  size: 15, color: Color(0xFF6366F1)),
            ),
            const SizedBox(width: 10),
            Text(
              'QLM',
              style: GoogleFonts.inter(
                fontSize: 18,
                fontWeight: FontWeight.w800,
                letterSpacing: 1,
              ),
            ),
          ],
        ),
        actions: [
          // Connection indicator
          Container(
            margin: const EdgeInsets.only(right: 16),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: server.isConnected
                  ? const Color(0xFF10B981).withOpacity(0.1)
                  : const Color(0xFFF43F5E).withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: server.isConnected
                    ? const Color(0xFF10B981).withOpacity(0.3)
                    : const Color(0xFFF43F5E).withOpacity(0.3),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: server.isConnected
                        ? const Color(0xFF10B981)
                        : const Color(0xFFF43F5E),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  server.isConnected ? 'Connected' : 'Offline',
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: server.isConnected
                        ? const Color(0xFF10B981)
                        : const Color(0xFFF43F5E),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
      body: IndexedStack(
        index: _selectedIndex,
        children: _primaryScreens,
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _selectedIndex,
        onDestinationSelected: (index) {
          if (index == 4) {
            _openMoreMenu();
          } else {
            setState(() => _selectedIndex = index);
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Dashboard',
          ),
          NavigationDestination(
            icon: Icon(Icons.storage_outlined),
            selectedIcon: Icon(Icons.storage),
            label: 'Data',
          ),
          NavigationDestination(
            icon: Icon(Icons.candlestick_chart_outlined),
            selectedIcon: Icon(Icons.candlestick_chart),
            label: 'Chart',
          ),
          NavigationDestination(
            icon: Icon(Icons.rocket_launch_outlined),
            selectedIcon: Icon(Icons.rocket_launch),
            label: 'Backtest',
          ),
          NavigationDestination(
            icon: Icon(Icons.more_horiz),
            selectedIcon: Icon(Icons.more_horiz),
            label: 'More',
          ),
        ],
      ),
    );
  }
}
