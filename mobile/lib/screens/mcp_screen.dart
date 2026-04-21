import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/mcp_provider.dart';
import '../core/constants.dart';

class McpScreen extends StatefulWidget {
  const McpScreen({super.key});

  @override
  State<McpScreen> createState() => _McpScreenState();
}

class _McpScreenState extends State<McpScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<McpProvider>().loadStatus();
    });
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text('MCP Service', style: GoogleFonts.inter(fontWeight: FontWeight.w700)),
      ),
      body: Consumer<McpProvider>(
        builder: (context, prov, _) {
          if (prov.loading && prov.status == null) {
            return const Center(child: CircularProgressIndicator());
          }

          final isActive = prov.isActive;

          return Column(
            children: [
              // Status Card
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? Colors.white.withOpacity(0.04) : Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0),
                  ),
                ),
                child: Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: (isActive ? AppConstants.statusOnline : const Color(0xFF64748B))
                            .withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Icon(
                        Icons.hub,
                        size: 22,
                        color: isActive ? AppConstants.statusOnline : const Color(0xFF64748B),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Service Status',
                            style: GoogleFonts.inter(
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                              color: isDark ? Colors.white : const Color(0xFF0F172A),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            isActive ? 'Online & Listening' : 'Offline',
                            style: GoogleFonts.inter(
                              fontSize: 12,
                              color: isActive ? AppConstants.statusOnline : const Color(0xFF64748B),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Switch(
                      value: isActive,
                      onChanged: (v) => prov.toggle(v),
                    ),
                  ],
                ),
              ),

              // Logs Header
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20),
                child: Row(
                  children: [
                    Text(
                      'ACTIVITY LOG',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 1,
                        color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                      ),
                    ),
                    const Spacer(),
                    Text(
                      '${prov.status?.logs.length ?? 0} entries',
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: isDark ? const Color(0xFF475569) : const Color(0xFFCBD5E1),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),

              // Log List
              Expanded(
                child: (prov.status?.logs.isEmpty ?? true)
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.list_alt,
                                size: 48,
                                color: isDark ? Colors.white.withOpacity(0.1) : Colors.black.withOpacity(0.1)),
                            const SizedBox(height: 12),
                            Text(
                              'No activity logs yet',
                              style: GoogleFonts.inter(
                                fontSize: 13,
                                color: isDark ? const Color(0xFF475569) : const Color(0xFFCBD5E1),
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: prov.status?.logs.length ?? 0,
                        itemBuilder: (context, i) {
                          final log = prov.status!.logs[i];
                          final isError = log.status == 'error';

                          return Container(
                            margin: const EdgeInsets.only(bottom: 8),
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: isDark ? Colors.white.withOpacity(0.03) : const Color(0xFFF8FAFC),
                              borderRadius: BorderRadius.circular(10),
                              border: Border.all(
                                color: isError
                                    ? AppConstants.chartRed.withOpacity(0.2)
                                    : (isDark ? Colors.white.withOpacity(0.04) : const Color(0xFFE2E8F0)),
                              ),
                            ),
                            child: Row(
                              children: [
                                Container(
                                  width: 6,
                                  height: 6,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: isError ? AppConstants.chartRed : AppConstants.statusOnline,
                                  ),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        log.action,
                                        style: GoogleFonts.inter(
                                          fontSize: 13,
                                          fontWeight: FontWeight.w500,
                                          color: isDark ? Colors.white : const Color(0xFF0F172A),
                                        ),
                                      ),
                                      const SizedBox(height: 2),
                                      Text(
                                        log.timestamp,
                                        style: GoogleFonts.jetBrainsMono(
                                          fontSize: 10,
                                          color: const Color(0xFF64748B),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                  decoration: BoxDecoration(
                                    color: (isError ? AppConstants.chartRed : AppConstants.statusOnline)
                                        .withOpacity(0.1),
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    log.status,
                                    style: GoogleFonts.inter(
                                      fontSize: 10,
                                      fontWeight: FontWeight.w600,
                                      color: isError ? AppConstants.chartRed : AppConstants.statusOnline,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}
