import 'package:flutter/material.dart';

/// Snackbar-based toast system matching the web UI Toast.
class AppToast {
  static void show(
    BuildContext context,
    String message, {
    ToastType type = ToastType.info,
    Duration duration = const Duration(seconds: 3),
  }) {
    final colors = _getColors(type);

    ScaffoldMessenger.of(context).hideCurrentSnackBar();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            Icon(colors.icon, color: colors.iconColor, size: 18),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
        backgroundColor: colors.bgColor,
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: BorderSide(color: colors.borderColor, width: 1),
        ),
        margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        duration: duration,
        dismissDirection: DismissDirection.horizontal,
      ),
    );
  }

  static void success(BuildContext context, String message) =>
      show(context, message, type: ToastType.success);

  static void error(BuildContext context, String message) =>
      show(context, message, type: ToastType.error);

  static void warning(BuildContext context, String message) =>
      show(context, message, type: ToastType.warning);

  static void info(BuildContext context, String message) =>
      show(context, message, type: ToastType.info);

  static _ToastColors _getColors(ToastType type) {
    switch (type) {
      case ToastType.success:
        return _ToastColors(
          bgColor: const Color(0xFF064E3B),
          iconColor: const Color(0xFF10B981),
          borderColor: const Color(0xFF10B981).withOpacity(0.3),
          icon: Icons.check_circle_outline,
        );
      case ToastType.error:
        return _ToastColors(
          bgColor: const Color(0xFF7F1D1D),
          iconColor: const Color(0xFFF43F5E),
          borderColor: const Color(0xFFF43F5E).withOpacity(0.3),
          icon: Icons.error_outline,
        );
      case ToastType.warning:
        return _ToastColors(
          bgColor: const Color(0xFF78350F),
          iconColor: const Color(0xFFF59E0B),
          borderColor: const Color(0xFFF59E0B).withOpacity(0.3),
          icon: Icons.warning_amber_outlined,
        );
      case ToastType.info:
        return _ToastColors(
          bgColor: const Color(0xFF1E293B),
          iconColor: const Color(0xFF6366F1),
          borderColor: const Color(0xFF6366F1).withOpacity(0.3),
          icon: Icons.info_outline,
        );
    }
  }
}

enum ToastType { success, error, warning, info }

class _ToastColors {
  final Color bgColor;
  final Color iconColor;
  final Color borderColor;
  final IconData icon;

  _ToastColors({
    required this.bgColor,
    required this.iconColor,
    required this.borderColor,
    required this.icon,
  });
}
