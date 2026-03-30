import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/server_provider.dart';
import '../themes/app_theme.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Settings'),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(vertical: 8),
        children: [
          _buildSectionHeader(context, "General"),
          _buildGeneralSection(context),
          const Divider(),

          _buildSectionHeader(context, "Appearance"),
          _buildAppearanceSection(context),
          const Divider(),

          _buildSectionHeader(context, "Server"),
          _buildServerSection(context),
          const Divider(),

          _buildSectionHeader(context, "Notifications"),
          _buildNotificationsSection(context),
          const Divider(),

          _buildSectionHeader(context, "About"),
          _buildAboutSection(context),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(BuildContext context, String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 8),
      child: Text(
        title,
        style: Theme.of(context).textTheme.titleSmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              fontWeight: FontWeight.bold,
            ),
      ),
    );
  }

  Widget _buildGeneralSection(BuildContext context) {
    return Column(
      children: [
        _buildListTile(
          context,
          icon: Icons.language,
          title: "Language",
          subtitle: "English",
          onTap: () => _showComingSoon(context),
        ),
        _buildSwitchTile(
          context,
          icon: Icons.fingerprint,
          title: "Biometric Authentication",
          subtitle: "Use fingerprint or face ID",
          value: false,
          onChanged: (value) {},
        ),
        _buildListTile(
          context,
          icon: Icons.data_saver_on,
          title: "Data Saver",
          subtitle: "Reduce data usage",
          onTap: () => _showComingSoon(context),
        ),
      ],
    );
  }

  Widget _buildAppearanceSection(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return Column(
          children: [
            _buildListTile(
              context,
              icon: Icons.brightness_6,
              title: "Theme",
              subtitle: themeProvider.themeModeOption == ThemeModeOption.light
                  ? "Light Mode"
                  : themeProvider.themeModeOption == ThemeModeOption.dark
                      ? "Dark Mode"
                      : "System Default",
              onTap: () => _showThemeDialog(context, themeProvider),
            ),
            _buildSwitchTile(
              context,
              icon: Icons.animation,
              title: "Animations",
              subtitle: "Enable smooth animations",
              value: true,
              onChanged: (value) {},
            ),
          ],
        );
      },
    );
  }

  Widget _buildServerSection(BuildContext context) {
    return Consumer<ServerProvider>(
      builder: (context, serverProvider, child) {
        return Column(
          children: [
            _buildListTile(
              context,
              icon: Icons.link,
              title: "Server URL",
              subtitle: serverProvider.serverUrl.isNotEmpty
                  ? serverProvider.serverUrl
                  : "Not Connected",
              onTap: () => _showServerDialog(context, serverProvider),
            ),
            _buildListTile(
              context,
              icon: Icons.dns,
              title: "Connection Status",
              subtitle: serverProvider.isConnected ? "Connected" : "Disconnected",
              onTap: () => {},
              trailing: Icon(
                serverProvider.isConnected
                    ? Icons.check_circle
                    : Icons.error,
                color: serverProvider.isConnected ? Colors.green : Colors.red,
              ),
            ),
            if (serverProvider.isConnected)
              _buildListTile(
                context,
                icon: Icons.refresh,
                title: "Reconnect",
                subtitle: "Reconnect to server",
                onTap: () => serverProvider.reconnect(),
              ),
          ],
        );
      },
    );
  }

  Widget _buildNotificationsSection(BuildContext context) {
    return Column(
      children: [
        _buildSwitchTile(
          context,
          icon: Icons.notifications_active,
          title: "Push Notifications",
          subtitle: "Receive trade alerts",
          value: true,
          onChanged: (value) {},
        ),
        _buildSwitchTile(
          context,
          icon: Icons.email,
          title: "Email Notifications",
          subtitle: "Daily summary emails",
          value: false,
          onChanged: (value) {},
        ),
        _buildSwitchTile(
          context,
          icon: Icons.sms,
          title: "SMS Alerts",
          subtitle: "Important trade notifications",
          value: false,
          onChanged: (value) {},
        ),
      ],
    );
  }

  Widget _buildAboutSection(BuildContext context) {
    return Column(
      children: [
        _buildListTile(
          context,
          icon: Icons.info,
          title: "Version",
          subtitle: "QLM Mobile v1.0.0",
          onTap: () {},
        ),
        _buildListTile(
          context,
          icon: Icons.article,
          title: "Terms of Service",
          subtitle: "View terms and conditions",
          onTap: () => _openUrl(context, "terms"),
        ),
        _buildListTile(
          context,
          icon: Icons.privacy_tip,
          title: "Privacy Policy",
          subtitle: "How we protect your data",
          onTap: () => _openUrl(context, "privacy"),
        ),
        _buildListTile(
          context,
          icon: Icons.headset_mic,
          title: "Support",
          subtitle: "Get help and report issues",
          onTap: () => _openUrl(context, "support"),
        ),
      ],
    );
  }

  Widget _buildListTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    Widget? trailing,
  }) {
    return ListTile(
      leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title),
      subtitle: Text(subtitle),
      trailing: trailing ?? Icon(Icons.arrow_forward),
      onTap: onTap,
    );
  }

  Widget _buildSwitchTile(
    BuildContext context, {
    required IconData icon,
    required String title,
    required String subtitle,
    required bool value,
    required ValueChanged<bool> onChanged,
  }) {
    return SwitchListTile(
      secondary: Icon(icon, color: Theme.of(context).colorScheme.primary),
      title: Text(title),
      subtitle: Text(subtitle),
      value: value,
      onChanged: onChanged,
    );
  }

  void _showThemeDialog(BuildContext context, ThemeProvider themeProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Select Theme'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile<ThemeModeOption>(
              title: const Text('Light Mode'),
              value: ThemeModeOption.light,
              groupValue: themeProvider.themeModeOption,
              onChanged: (value) {
                themeProvider.setThemeMode(ThemeModeOption.light);
                Navigator.pop(context);
              },
            ),
            RadioListTile<ThemeModeOption>(
              title: const Text('Dark Mode'),
              value: ThemeModeOption.dark,
              groupValue: themeProvider.themeModeOption,
              onChanged: (value) {
                themeProvider.setThemeMode(ThemeModeOption.dark);
                Navigator.pop(context);
              },
            ),
            RadioListTile<ThemeModeOption>(
              title: const Text('System Default'),
              value: ThemeModeOption.system,
              groupValue: themeProvider.themeModeOption,
              onChanged: (value) {
                themeProvider.setThemeMode(ThemeModeOption.system);
                Navigator.pop(context);
              },
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  void _showServerDialog(BuildContext context, ServerProvider serverProvider) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Server Connection'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (serverProvider.isConnected)
              ListTile(
                title: Text('Connected'),
                subtitle: Text(serverProvider.serverUrl),
                leading: Icon(Icons.check_circle, color: Colors.green),
              )
            else
              ListTile(
                title: Text('Disconnected'),
                leading: Icon(Icons.error, color: Colors.red),
              ),
            const SizedBox(height: 16),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.pop(context);
                serverProvider.disconnect();
                Navigator.pushReplacementNamed(context, '/connection');
              },
              icon: Icon(Icons.link),
              label: const Text('Change Server'),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Feature coming soon!'),
        duration: Duration(seconds: 2),
      ),
    );
  }

  void _openUrl(BuildContext context, String page) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Opening $page...'),
        duration: const Duration(seconds: 2),
      ),
    );
  }
}

// Mock icon for biometric
class Icons {
  IconData get biometric_icon => Icons.fingerprint;
}