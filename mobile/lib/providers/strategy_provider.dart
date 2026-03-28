import 'package:flutter/material.dart';
import '../core/api_client.dart';
import '../models/strategy.dart';

class StrategyProvider extends ChangeNotifier {
  List<Strategy> _strategies = [];
  String _currentCode = '';
  String _currentName = '';
  int _currentVersion = 1;
  List<String> _templates = [];
  bool _loading = false;
  String? _error;

  List<Strategy> get strategies => _strategies;
  String get currentCode => _currentCode;
  String get currentName => _currentName;
  int get currentVersion => _currentVersion;
  List<String> get templates => _templates;
  bool get loading => _loading;
  String? get error => _error;

  Future<void> loadStrategies() async {
    _loading = true;
    notifyListeners();

    try {
      final data = await apiClient.get('/strategies/');
      _strategies = (data as List<dynamic>)
          .map((e) => Strategy.fromJson(Map<String, dynamic>.from(e as Map)))
          .toList();
    } catch (e) {
      _error = e.toString();
    }

    _loading = false;
    notifyListeners();
  }

  Future<void> loadCode(String name, int version) async {
    try {
      final res = await apiClient.get('/strategies/$name/$version');
      _currentCode = res['code']?.toString() ?? '';
      _currentName = name;
      _currentVersion = version;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      notifyListeners();
    }
  }

  void setCode(String code) {
    _currentCode = code;
    notifyListeners();
  }

  void setName(String name) {
    _currentName = name;
    notifyListeners();
  }

  void createNew() {
    _currentName = '';
    _currentCode = '''from backend.core.strategy import Strategy
import pandas as pd
import numpy as np

class NewStrategy(Strategy):
    """
    New Strategy
    """
    def define_variables(self, df):
        return {}

    def entry_long(self, df, vars):
        return pd.Series([False] * len(df), index=df.index)

    def entry_short(self, df, vars):
        return pd.Series([False] * len(df), index=df.index)

    def exit(self, df, vars, trade):
        return False

    def risk_model(self, df, vars):
        return {}
''';
    notifyListeners();
  }

  Future<bool> save() async {
    if (_currentName.isEmpty) return false;

    try {
      await apiClient.post('/strategies/', body: {
        'name': _currentName,
        'code': _currentCode,
      });
      await loadStrategies();
      return true;
    } catch (e) {
      _error = e.toString();
      notifyListeners();
      return false;
    }
  }

  Future<Map<String, dynamic>?> validate() async {
    try {
      final res = await apiClient.post('/strategies/validate', body: {
        'name': 'validation_check',
        'code': _currentCode,
      });
      return Map<String, dynamic>.from(res as Map);
    } catch (e) {
      return {'valid': false, 'error': e.toString()};
    }
  }

  Future<bool> deleteStrategy(String name) async {
    try {
      await apiClient.delete('/strategies/$name');
      _strategies.removeWhere((s) => s.name == name);
      if (_currentName == name) createNew();
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      return false;
    }
  }

  Future<void> loadTemplates() async {
    try {
      final data = await apiClient.get('/strategies/templates/list');
      _templates = (data as List<dynamic>).map((e) => e.toString()).toList();
      notifyListeners();
    } catch (e) {
      _templates = [];
    }
  }

  Future<void> applyTemplate(String name) async {
    try {
      final res = await apiClient.get('/strategies/templates/$name');
      _currentCode = res['code']?.toString() ?? '';
      _currentName = '${name.toUpperCase()}_Strategy';
      notifyListeners();
    } catch (e) {
      _error = e.toString();
    }
  }
}
