import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:google_fonts/google_fonts.dart';
import '../providers/mcp_provider.dart';

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
      appBar: AppBar(title: const Text('MCP Service')),
      body: Consumer<McpProvider>(
        builder: (context, prov, _) {
          if (prov.loading && prov.status == null) {
            return const Center(child: CircularProgressIndicator());
          }

          final isActive = prov.isActive;

          return Column(
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                margin: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: isDark ? const Color(0xFF1E293B) : Colors.white,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Service Status', style: GoogleFonts.inter(fontWeight: FontWeight.bold)),
                        Text(isActive ? 'Online & Listening' : 'Offline', 
                          style: TextStyle(color: isActive ? Colors.green : Colors.grey)),
                      ],
                    ),
                    Switch(
                      value: isActive,
                      onChanged: (v) => prov.toggle(v),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: prov.status?.logs.length ?? 0,
                  itemBuilder: (context, i) {
                    final log = prov.status!.logs[i];
                    return ListTile(
                      title: Text(log.action, style: GoogleFonts.inter(fontSize: 14)),
                      subtitle: Text(log.timestamp, style: GoogleFonts.jetBrainsMono(fontSize: 10)),
                      trailing: Text(log.status, style: TextStyle(
                        color: log.status == 'error' ? Colors.red : Colors.grey,
                        fontSize: 12
                      )),
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
