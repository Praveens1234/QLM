import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/theme.dart';
import 'providers/server_provider.dart';
import 'providers/theme_provider.dart';
import 'providers/dashboard_provider.dart';
import 'providers/data_provider.dart';
import 'providers/strategy_provider.dart';
import 'providers/backtest_provider.dart';
import 'providers/chart_provider.dart';
import 'providers/inspector_provider.dart';
import 'providers/mcp_provider.dart';
import 'screens/server_connect_screen.dart';
import 'screens/main_shell.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const QlmApp());
}

class QlmApp extends StatelessWidget {
  const QlmApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ServerProvider()..autoConnect()),
        ChangeNotifierProvider(create: (_) => ThemeProvider()),
        ChangeNotifierProvider(create: (_) => DashboardProvider()),
        ChangeNotifierProvider(create: (_) => DataProvider()),
        ChangeNotifierProvider(create: (_) => StrategyProvider()),
        ChangeNotifierProvider(create: (_) => BacktestProvider()),
        ChangeNotifierProvider(create: (_) => ChartProvider()),
        ChangeNotifierProvider(create: (_) => InspectorProvider()),
        ChangeNotifierProvider(create: (_) => McpProvider()),
      ],
      child: Consumer<ThemeProvider>(
        builder: (context, theme, _) {
          return MaterialApp(
            title: 'QLM',
            debugShowCheckedModeBanner: false,
            // Theme Configuration
            themeMode: theme.themeMode,
            theme: AppTheme.lightTheme,
            darkTheme: AppTheme.darkTheme,
            
            // Routing
            initialRoute: '/',
            routes: {
              '/': (context) => const ServerConnectScreen(),
              '/main': (context) => const MainShell(),
            },
          );
        },
      ),
    );
  }
}
