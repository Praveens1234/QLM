import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/monokai-sublime.dart';
import 'package:flutter_highlight/themes/github.dart';
import 'package:google_fonts/google_fonts.dart';

/// Code editor with Python syntax highlighting.
class CodeEditorWidget extends StatelessWidget {
  final String code;
  final ValueChanged<String>? onChanged;
  final bool readOnly;

  const CodeEditorWidget({
    super.key,
    required this.code,
    this.onChanged,
    this.readOnly = false,
  });

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (readOnly || onChanged == null) {
      return Container(
        width: double.infinity,
        decoration: BoxDecoration(
          color: isDark ? const Color(0xFF0F172A) : const Color(0xFFFAFAFA),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0),
          ),
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(12),
          scrollDirection: Axis.horizontal,
          child: SingleChildScrollView(
            child: HighlightView(
              code,
              language: 'python',
              theme: isDark ? monokaiSublimeTheme : githubTheme,
              textStyle: GoogleFonts.jetBrainsMono(fontSize: 13, height: 1.5),
              padding: EdgeInsets.zero,
            ),
          ),
        ),
      );
    }

    // Editable mode
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF0F172A) : const Color(0xFFFAFAFA),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isDark ? Colors.white.withOpacity(0.06) : const Color(0xFFE2E8F0),
        ),
      ),
      child: TextField(
        controller: TextEditingController(text: code),
        onChanged: onChanged,
        maxLines: null,
        expands: true,
        keyboardType: TextInputType.multiline,
        style: GoogleFonts.jetBrainsMono(
          fontSize: 13,
          height: 1.5,
          color: isDark ? const Color(0xFFE2E8F0) : const Color(0xFF1E293B),
        ),
        decoration: const InputDecoration(
          border: InputBorder.none,
          contentPadding: EdgeInsets.all(12),
        ),
      ),
    );
  }
}
