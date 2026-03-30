import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:lottie/lottie.dart';
import '../providers/server_provider.dart';
import '../themes/app_theme.dart';

class ConnectionScreen extends StatefulWidget {
  const ConnectionScreen({super.key});

  @override
  State<ConnectionScreen> createState() => _ConnectionScreenState();
}

class _ConnectionScreenState extends State<ConnectionScreen> {
  final _formKey = GlobalKey<FormState>();
  final _urlController = TextEditingController();
  final _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    _urlController.text = 'http://localhost:3000'; // Default for local development
  }

  @override
  void dispose() {
    _urlController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24.0),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _buildHeader(context),
                const SizedBox(height: 48),
                _buildForm(context),
                const SizedBox(height: 24),
                _buildTipsCard(context),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Column(
      children: [
        Lottie.asset(
          'assets/animations/connection.json',
          height: 200,
          fit: BoxFit.contain,
        ),
        const SizedBox(height: 24),
        Text(
          'Connect to QLM Server',
          style: Theme.of(context).textTheme.displaySmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 12),
        Text(
          'Enter your QLM server URL to get started',
          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
          textAlign: TextAlign.center,
        ),
      ],
    );
  }

  Widget _buildForm(BuildContext context) {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TextFormField(
            controller: _urlController,
            focusNode: _focusNode,
            decoration: InputDecoration(
              labelText: 'Server URL',
              hintText: 'http://localhost:3000',
              prefixIcon: const Icon(Icons.link_rounded),
              suffixIcon: IconButton(
                icon: const Icon(Icons.paste_rounded),
                onPressed: _pasteFromClipboard,
                tooltip: 'Paste from clipboard',
              ),
            ),
            keyboardType: TextInputType.url,
            textInputAction: TextInputAction.go,
            autofillHints: const [AutofillHints.url],
            validator: _validateUrl,
            onFieldSubmitted: (_) => _attemptConnection(),
            onChanged: (_) {
              if (Provider.of<ServerProvider>(context, listen: false).hasError) {
                Provider.of<ServerProvider>(context, listen: false).clearError();
              }
            },
          ),
          const SizedBox(height: 16),
          Builder(
            builder: (context) {
              final serverProvider = Provider.of<ServerProvider>(context);

              if (serverProvider.hasError) {
                return Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Material(
                    color: Theme.of(context).colorScheme.errorContainer,
                    borderRadius: BorderRadius.circular(12),
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.error_outline_rounded,
                            color: Theme.of(context).colorScheme.error,
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Text(
                              serverProvider.errorMessage!,
                              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close_rounded, size: 20),
                            onPressed: serverProvider.clearError,
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }

              return const SizedBox.shrink();
            },
          ),
          SizedBox(
            height: 56,
            child: Consumer<ServerProvider>(
              builder: (context, serverProvider, child) {
                if (serverProvider.isConnecting) {
                  return ElevatedButton(
                    onPressed: null,
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(
                            strokeWidth: 2,
                            valueColor: AlwaysStoppedAnimation<Color>(
                              Theme.of(context).colorScheme.onPrimary,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        const Text('Connecting...'),
                      ],
                    ),
                  );
                }

                return ElevatedButton(
                  onPressed: _attemptConnection,
                  child: const Text(
                    'Connect',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                  ),
                );
              },
            ),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: _tryLocalhostConnection,
            child: const Text('Use Localhost (127.0.0.1:3000)'),
          ),
        ],
      ),
    );
  }

  Widget _buildTipsCard(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceVariant.withOpacity(0.5),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Quick Tips',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            _buildTipRow(
              context,
              'Local Server',
              'Use http://localhost:3000 or http://127.0.0.1:3000',
              Icons.computer,
            ),
            const SizedBox(height: 12),
            _buildTipRow(
              context,
              'Network Server',
              'Use http://192.168.x.x:3000 or your public domain',
              Icons.router,
            ),
            const SizedBox(height: 12),
            _buildTipRow(
              context,
              'HTTPS',
              'For production, use https://your-domain.com',
              Icons.verified,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTipRow(BuildContext context, String title, String subtitle, IconData icon) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 20,
          color: Theme.of(context).colorScheme.primary,
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              Text(
                subtitle,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  String? _validateUrl(String? value) {
    if (value == null || value.isEmpty) {
      return 'Please enter a server URL';
    }

    final sanitized = value.trim();
    if (!sanitized.startsWith('http://') && !sanitized.startsWith('https://')) {
      return 'URL must start with http:// or https://';
    }

    final uri = Uri.tryParse(sanitized);
    if (uri == null || !uri.hasAuthority || uri.host.isEmpty) {
      return 'Please enter a valid URL';
    }

    return null;
  }

  Future<void> _pasteFromClipboard() async {
    final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
    if (clipboardData?.text != null) {
      _urlController.text = clipboardData!.text!;
      _urlController.selection = TextSelection.fromPosition(
        TextPosition(offset: _urlController.text.length),
      );
    }
  }

  Future<void> _attemptConnection() async {
    if (_formKey.currentState?.validate() ?? false) {
      final url = _urlController.text.trim();
      final connected = await Provider.of<ServerProvider>(context, listen: false)
          .connect(url);

      if (connected && mounted) {
        Navigator.pushReplacementNamed(context, '/home');
      }
    }
  }

  void _tryLocalhostConnection() {
    _urlController.text = 'http://127.0.0.1:3000';
    _urlController.selection = TextSelection.fromPosition(
      TextPosition(offset: _urlController.text.length),
    );
    FocusScope.of(context).requestFocus(_focusNode);
  }
}