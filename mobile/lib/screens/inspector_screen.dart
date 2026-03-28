import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class InspectorScreen extends StatelessWidget {
  const InspectorScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Data Inspector')),
      body: Center(
        child: Text(
          'Data Inspector logic porting...',
          style: GoogleFonts.inter(color: Colors.grey),
        ),
      ),
    );
  }
}
