import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/server_provider.dart';
import '../core/constants.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Settings',
          style: GoogleFonts.inter(fontWeight: FontWeight.w700),
        ),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        children: [
          // Appearance Section
          _buildSectionHeader(context, 'Appearance'),
          const SizedBox(height: 8),
          _buildCard(
            context,
            child: Consumer<ThemeProvider>(
              builder: (context, theme, _) => Column(
                children: [
                  _buildThemeOption(context, theme, ThemeMode.system, Icons.brightness_auto, 'System Default'),
                  Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                  _buildThemeOption(context, theme, ThemeMode.light, Icons.light_mode, 'Light'),
                  Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                  _buildThemeOption(context, theme, ThemeMode.dark, Icons.dark_mode, 'Dark'),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Connection Section
          _buildSectionHeader(context, 'Server Connection'),
          const SizedBox(height: 8),
          _buildCard(
            context,
            child: Consumer<ServerProvider>(
              builder: (context, server, _) => Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Container(
                          width: 40,
                          height: 40,
                          decoration: BoxDecoration(
                            color: server.isConnected
                                ? AppConstants.statusOnline.withOpacity(0.1)
                                : AppConstants.statusOffline.withOpacity(0.1),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(
                            Icons.dns_outlined,
                            size: 20,
                            color: server.isConnected
                                ? AppConstants.statusOnline
                                : AppConstants.statusOffline,
                          ),
                        ),
                        const SizedBox(width: 14),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                server.isConnected ? 'Connected' : 'Disconnected',
                                style: GoogleFonts.inter(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: isDark ? Colors.white : const Color(0xFF0F172A),
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                server.serverUrl.isNotEmpty ? server.serverUrl : 'No server configured',
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 12,
                                  color: const Color(0xFF64748B),
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                  Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                  ListTile(
                    leading: const Icon(Icons.logout, color: Color(0xFFF43F5E), size: 20),
                    title: Text(
                      'Disconnect & Sign Out',
                      style: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: const Color(0xFFF43F5E),
                      ),
                    ),
                    onTap: () {
                      showDialog<bool>(
                        context: context,
                        builder: (ctx) => AlertDialog(
                          title: Text('Disconnect?', style: GoogleFonts.inter(fontWeight: FontWeight.w600)),
                          content: const Text('You will be returned to the connection screen.'),
                          actions: [
                            TextButton(
                              onPressed: () => Navigator.pop(ctx, false),
                              child: const Text('Cancel'),
                            ),
                            TextButton(
                              onPressed: () => Navigator.pop(ctx, true),
                              style: TextButton.styleFrom(foregroundColor: const Color(0xFFF43F5E)),
                              child: const Text('Disconnect'),
                            ),
                          ],
                        ),
                      ).then((confirmed) {
                        if (confirmed == true && context.mounted) {
                          context.read<ServerProvider>().disconnect();
                          Navigator.of(context).pushReplacementNamed('/');
                        }
                      });
                    },
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(height: 24),

          // About Section
          _buildSectionHeader(context, 'About'),
          const SizedBox(height: 8),
          _buildCard(
            context,
            child: Column(
              children: [
                _buildInfoTile(context, 'App Name', AppConstants.appFullName),
                Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                _buildInfoTile(context, 'Version', 'v1.0.1'),
                Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                _buildInfoTile(context, 'Framework', 'Flutter'),
                Divider(height: 1, color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0)),
                _buildInfoTile(context, 'Platform', 'Android'),
              ],
            ),
          ),

          const SizedBox(height: 32),

          // App logo
          Center(
            child: Column(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: const Color(0xFF6366F1).withOpacity(0.1),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.candlestick_chart, color: Color(0xFF6366F1), size: 24),
                ),
                const SizedBox(height: 8),
                Text(
                  'QLM',
                  style: GoogleFonts.inter(
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 2,
                    color: isDark ? const Color(0xFF475569) : const Color(0xFFCBD5E1),
                  ),
                ),
                Text(
                  'QuantLogic Mobile',
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    color: isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        title.toUpperCase(),
        style: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          letterSpacing: 1,
          color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
        ),
      ),
    );
  }

  Widget _buildCard(BuildContext context, {required Widget child}) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      decoration: BoxDecoration(
        color: isDark ? Colors.white.withOpacity(0.04) : Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0),
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }

  Widget _buildThemeOption(BuildContext context, ThemeProvider theme, ThemeMode mode, IconData icon, String label) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isSelected = theme.themeMode == mode;

    return ListTile(
      leading: Icon(icon, size: 20, color: isSelected ? const Color(0xFF6366F1) : (isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8))),
      title: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 14,
          fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
          color: isDark ? Colors.white : const Color(0xFF0F172A),
        ),
      ),
      trailing: isSelected
          ? const Icon(Icons.check_circle, color: Color(0xFF6366F1), size: 20)
          : null,
      onTap: () => theme.setThemeMode(mode),
    );
  }

  Widget _buildInfoTile(BuildContext context, String label, String value) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.inter(
              fontSize: 14,
              color: isDark ? const Color(0xFF94A3B8) : const Color(0xFF64748B),
            ),
          ),
          Text(
            value,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: isDark ? Colors.white : const Color(0xFF0F172A),
            ),
          ),
        ],
      ),
    );
  }
}
