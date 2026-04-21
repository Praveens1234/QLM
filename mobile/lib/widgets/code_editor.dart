import 'package:flutter/material.dart';
import 'package:flutter_highlight/flutter_highlight.dart';
import 'package:flutter_highlight/themes/monokai-sublime.dart';
import 'package:flutter_highlight/themes/github.dart';
import 'package:google_fonts/google_fonts.dart';

/// Code editor with Python syntax highlighting.
/// Uses a persistent TextEditingController so cursor position and focus
/// are preserved across rebuilds.
class CodeEditorWidget extends StatefulWidget {
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
  State<CodeEditorWidget> createState() => _CodeEditorWidgetState();
}

class _CodeEditorWidgetState extends State<CodeEditorWidget> {
  late TextEditingController _controller;
  bool _isInternalUpdate = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.code);
    _controller.addListener(_onControllerChanged);
  }

  @override
  void didUpdateWidget(covariant CodeEditorWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Only update text when the code changes externally (e.g. loading a
    // different strategy), not when the user is typing.
    if (widget.code != oldWidget.code && widget.code != _controller.text) {
      _isInternalUpdate = true;
      _controller.text = widget.code;
      _isInternalUpdate = false;
    }
  }

  void _onControllerChanged() {
    if (_isInternalUpdate) return;
    widget.onChanged?.call(_controller.text);
  }

  @override
  void dispose() {
    _controller.removeListener(_onControllerChanged);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    if (widget.readOnly || widget.onChanged == null) {
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
              widget.code,
              language: 'python',
              theme: isDark ? monokaiSublimeTheme : githubTheme,
              textStyle: GoogleFonts.jetBrainsMono(fontSize: 13, height: 1.5),
              padding: EdgeInsets.zero,
            ),
          ),
        ),
      );
    }

    // Editable mode with persistent controller
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
        controller: _controller,
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
