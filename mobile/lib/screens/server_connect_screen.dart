import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../providers/server_provider.dart';


class ServerConnectScreen extends StatefulWidget {
  const ServerConnectScreen({super.key});

  @override
  State<ServerConnectScreen> createState() => _ServerConnectScreenState();
}

class _ServerConnectScreenState extends State<ServerConnectScreen>
    with SingleTickerProviderStateMixin {
  final _urlController = TextEditingController();
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    // Pre-fill saved URL and listen for auto-connect
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final server = context.read<ServerProvider>();
      if (server.serverUrl.isNotEmpty) {
        _urlController.text = server.serverUrl;
      }
      
      // Auto-redirect if already connected (or when it connects)
      if (server.isConnected) {
        Navigator.of(context).pushReplacementNamed('/main');
      }
      server.addListener(_serverListener);
    });
  }

  void _serverListener() {
    if (!mounted) return;
    final server = context.read<ServerProvider>();
    if (server.isConnected) {
      server.removeListener(_serverListener);
      Navigator.of(context).pushReplacementNamed('/main');
    }
  }

  @override
  void dispose() {
    final server = context.read<ServerProvider>();
    server.removeListener(_serverListener);
    _urlController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Future<void> _connect() async {
    final url = _urlController.text.trim();
    if (url.isEmpty) return;

    final server = context.read<ServerProvider>();
    final success = await server.connect(url);

    if (success && mounted) {
      Navigator.of(context).pushReplacementNamed('/main');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Logo / Brand
                AnimatedBuilder(
                  listenable: _pulseController,
                  builder: (context, _) {
                    return Container(
                      width: 80,
                      height: 80,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            const Color(0xFF6366F1).withOpacity(
                                0.3 + _pulseController.value * 0.2),
                            const Color(0xFF6366F1).withOpacity(0.05),
                          ],
                        ),
                      ),
                      child: const Icon(
                        Icons.candlestick_chart,
                        size: 36,
                        color: Color(0xFF6366F1),
                      ),
                    );
                  },
                ),
                const SizedBox(height: 24),

                // Title
                Text(
                  'QLM',
                  style: GoogleFonts.inter(
                    fontSize: 36,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 4,
                    color: isDark ? Colors.white : Colors.black87,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'QuantLogic Mobile v1.0.1',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    fontWeight: FontWeight.w400,
                    color: isDark ? const Color(0xFF64748B) : const Color(0xFF94A3B8),
                    letterSpacing: 1,
                  ),
                ),
                const SizedBox(height: 48),

                // Server URL Input
                TextField(
                  controller: _urlController,
                  keyboardType: TextInputType.url,
                  textInputAction: TextInputAction.go,
                  onSubmitted: (_) => _connect(),
                  style: GoogleFonts.jetBrainsMono(fontSize: 14),
                  decoration: InputDecoration(
                    labelText: 'Server URL',
                    hintText: 'http://192.168.1.5:8010',
                    prefixIcon: const Icon(Icons.dns_outlined, size: 20),
                    suffixIcon: Consumer<ServerProvider>(
                      builder: (context, server, _) {
                        if (server.status == ServerStatus.connecting) {
                          return const Padding(
                            padding: EdgeInsets.all(12),
                            child: SizedBox(
                              width: 20,
                              height: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            ),
                          );
                        }
                        if (server.status == ServerStatus.connected) {
                          return const Icon(Icons.check_circle,
                              color: Color(0xFF10B981));
                        }
                        return const SizedBox.shrink();
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                // Error message
                Consumer<ServerProvider>(
                  builder: (context, server, _) {
                    if (server.status == ServerStatus.error) {
                      return Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(12),
                        margin: const EdgeInsets.only(bottom: 16),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF43F5E).withOpacity(0.1),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: const Color(0xFFF43F5E).withOpacity(0.2),
                          ),
                        ),
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline,
                                color: Color(0xFFF43F5E), size: 16),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                server.errorMessage,
                                style: GoogleFonts.inter(
                                  fontSize: 12,
                                  color: const Color(0xFFF43F5E),
                                ),
                              ),
                            ),
                          ],
                        ),
                      );
                    }
                    return const SizedBox.shrink();
                  },
                ),

                // Connect Button
                Consumer<ServerProvider>(
                  builder: (context, server, _) {
                    final isConnecting = server.status == ServerStatus.connecting;
                    return SizedBox(
                      width: double.infinity,
                      height: 52,
                      child: ElevatedButton(
                        onPressed: isConnecting ? null : _connect,
                        child: isConnecting
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                  color: Colors.white,
                                ),
                              )
                            : Text(
                                'Connect',
                                style: GoogleFonts.inter(
                                  fontSize: 15,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                      ),
                    );
                  },
                ),

                const SizedBox(height: 32),

                // Hint
                Text(
                  'Enter the URL of your QLM server\nrunning on your local network or cloud',
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: isDark ? const Color(0xFF475569) : const Color(0xFF94A3B8),
                    height: 1.5,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Reusable AnimatedBuilder
class AnimatedBuilder extends AnimatedWidget {
  final Widget Function(BuildContext context, Widget? child) builder;
  const AnimatedBuilder({super.key, required super.listenable, required this.builder});
  @override
  Widget build(BuildContext context) => builder(context, null);
}
