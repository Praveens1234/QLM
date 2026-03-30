import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:shared_preferences/shared_preferences.dart';

enum ThemeModeOption { light, dark, system }

class ThemeProvider extends ChangeNotifier {
  final SharedPreferences _prefs;
  ThemeModeOption _themeModeOption = ThemeModeOption.system;
  ThemeMode _themeMode = ThemeMode.system;

  ThemeProvider(this._prefs) {
    _loadTheme();
  }

  void _loadTheme() {
    final savedTheme = _prefs.getString('themeMode') ?? 'system';
    _themeModeOption = ThemeModeOption.values.firstWhere(
      (e) => e.toString() == 'ThemeModeOption.$savedTheme',
      orElse: () => ThemeModeOption.system,
    );

    _updateThemeMode();
  }

  void _updateThemeMode() {
    switch (_themeModeOption) {
      case ThemeModeOption.light:
        _themeMode = ThemeMode.light;
        break;
      case ThemeModeOption.dark:
        _themeMode = ThemeMode.dark;
        break;
      case ThemeModeOption.system:
        _themeMode = ThemeMode.system;
        break;
    }
    notifyListeners();
  }

  ThemeModeOption get themeModeOption => _themeModeOption;
  ThemeMode get themeMode => _themeMode;

  bool get isDarkMode {
    if (_themeMode == ThemeMode.system) {
      return SchedulerBinding.instance.platformDispatcher.platformBrightness ==
          Brightness.dark;
    }
    return _themeMode == ThemeMode.dark;
  }

  Future<void> setThemeMode(ThemeModeOption option) async {
    _themeModeOption = option;
    _updateThemeMode();
    await _prefs.setString('themeMode', option.toString().split('.').last);
  }

  Future<void> toggleTheme() async {
    switch (_themeModeOption) {
      case ThemeModeOption.light:
        await setThemeMode(ThemeModeOption.dark);
        break;
      case ThemeModeOption.dark:
        await setThemeMode(ThemeModeOption.system);
        break;
      case ThemeModeOption.system:
        await setThemeMode(ThemeModeOption.light);
        break;
    }
  }
}