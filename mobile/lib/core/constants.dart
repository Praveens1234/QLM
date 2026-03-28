import 'package:flutter/material.dart';

// ─── App Identity ───────────────────────────────────────────
class AppConstants {
  static const String appName = 'QLM';
  static const String appFullName = 'QuantLogic Mobile';
  static const String appVersion = '1.0.0';

  // ─── Spacing ────────────────────────────────────────────
  static const double spacingXs = 4.0;
  static const double spacingSm = 8.0;
  static const double spacingMd = 12.0;
  static const double spacingLg = 16.0;
  static const double spacingXl = 24.0;
  static const double spacingXxl = 32.0;

  // ─── Border Radius ──────────────────────────────────────
  static const double radiusSm = 8.0;
  static const double radiusMd = 12.0;
  static const double radiusLg = 16.0;
  static const double radiusXl = 20.0;
  static const double radiusFull = 100.0;

  // ─── Chart Colors ──────────────────────────────────────
  static const Color chartGreen = Color(0xFF10B981);
  static const Color chartRed = Color(0xFFF43F5E);
  static const Color chartVolume = Color(0xFF4F46E5);
  static const Color chartGrid = Color(0x0AFFFFFF);
  static const Color chartCrosshair = Color(0x4D94A3B8);

  // ─── Indicator Colors ──────────────────────────────────
  static const Color sma50Color = Color(0xFF38BDF8);
  static const Color ema20Color = Color(0xFFFCD34D);
  static const Color ema50Color = Color(0xFFF472B6);
  static const Color ema200Color = Color(0xFFA78BFA);
  static const Color bbColor = Color(0x8038BDF8);
  static const Color rsiColor = Color(0xFFEC4899);

  // ─── Status Colors ─────────────────────────────────────
  static const Color statusOnline = Color(0xFF10B981);
  static const Color statusOffline = Color(0xFFF43F5E);
  static const Color statusWarning = Color(0xFFF59E0B);

  // ─── API Timeouts ──────────────────────────────────────
  static const Duration apiTimeout = Duration(seconds: 30);
  static const Duration backtestTimeout = Duration(seconds: 300);
  static const Duration healthCheckTimeout = Duration(seconds: 10);
}
