import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../providers/theme_provider.dart';
import '../providers/server_provider.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // Theme
          Consumer<ThemeProvider>(
            builder: (context, theme, _) => ListTile(
              leading: const Icon(Icons.palette),
              title: const Text('Appearance'),
              trailing: DropdownButton<ThemeMode>(
                value: theme.themeMode,
                items: const [
                  DropdownMenuItem(value: ThemeMode.system, child: Text('System')),
                  DropdownMenuItem(value: ThemeMode.light, child: Text('Light')),
                  DropdownMenuItem(value: ThemeMode.dark, child: Text('Dark')),
                ],
                onChanged: (v) {
                  if (v != null) theme.setThemeMode(v);
                },
              ),
            ),
          ),
          const Divider(),
          // Server
          Consumer<ServerProvider>(
            builder: (context, server, _) => ListTile(
              leading: const Icon(Icons.dns),
              title: const Text('Server Connection'),
              subtitle: Text(server.serverUrl),
              trailing: IconButton(
                icon: const Icon(Icons.logout, color: Colors.red),
                onPressed: () {
                  server.disconnect();
                  Navigator.of(context).pushReplacementNamed('/');
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
