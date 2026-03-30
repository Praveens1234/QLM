import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'themes/app_theme.dart';
import 'providers/server_provider.dart';
import 'providers/theme_provider.dart';
import 'screens/connection_screen.dart';
import 'screens/home_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/data_manager_screen.dart';
import 'screens/strategy_lab_screen.dart';
import 'screens/chart_viewer_screen.dart';
import 'screens/backtest_runner_screen.dart';
import 'screens/data_inspector_screen.dart';
import 'screens/mcp_service_screen.dart';
import 'screens/settings_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  final prefs = await SharedPreferences.getInstance();
  final isConnected = prefs.getBool('isConnected') ?? false;
  final savedUrl = prefs.getString('serverUrl') ?? '';

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ThemeProvider(prefs)),
        ChangeNotifierProvider(create: (_) => ServerProvider(prefs, savedUrl, isConnected)),
      ],
      child: const QLMApp(),
    ),
  );
}

class QLMApp extends StatelessWidget {
  const QLMApp({super.key});

  @override
  Widget build(BuildContext context) {
    return Consumer<ThemeProvider>(
      builder: (context, themeProvider, child) {
        return MaterialApp(
          title: 'QLM Mobile',
          debugShowCheckedModeBanner: false,

          // Material You (Material 3) Theme
          themeMode: themeProvider.themeMode,
          theme: AppTheme.lightTheme,
          darkTheme: AppTheme.darkTheme,

          // Custom scroll behavior for better UX
          scrollBehavior: const MaterialScrollBehavior().copyWith(
            physics: const BouncingScrollPhysics(),
          ),

          // Initial route based on connection status
          home: Consumer<ServerProvider>(
            builder: (context, serverProvider, child) {
              if (serverProvider.isConnected) {
                return const HomeScreen();
              }
              return const ConnectionScreen();
            },
          ),

          // Named routes for navigation
          routes: {
            '/connection': (context) => const ConnectionScreen(),
            '/home': (context) => const HomeScreen(),
            '/dashboard': (context) => const DashboardScreen(),
            '/data-manager': (context) => const DataManagerScreen(),
            '/strategy-lab': (context) => const StrategyLabScreen(),
            '/chart-viewer': (context) => const ChartViewerScreen(),
            '/backtest-runner': (context) => const BacktestRunnerScreen(),
            '/data-inspector': (context) => const DataInspectorScreen(),
            '/mcp-service': (context) => const McpServiceScreen(),
            '/settings': (context) => const SettingsScreen(),
          },

          // Navigation theme
          builder: (context, child) {
            return MediaQuery(
              data: MediaQuery.of(context).copyWith(
                textScaler: MediaQuery.of(context).textScaler.clamp(
                  minScaleFactor: 0.8,
                  maxScaleFactor: 1.2,
                ),
              ),
              child: child!,
            );
          },
        );
      },
    );
  }
}