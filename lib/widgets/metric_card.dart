import 'package:flutter/material.dart';
import 'package:material_color_utilities/material_color_utilities.dart';

enum ChangeType { positive, negative, neutral }

class MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final String change;
  final ChangeType changeType;

  const MetricCard({
    super.key,
    required this.title,
    required this.value,
    required this.icon,
    required this.change,
    required this.changeType,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.surface,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
                Icon(
                  icon,
                  size: 24,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ],
            ),
            const SizedBox(height: 16),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _buildChangeChip(context),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChangeChip(BuildContext context) {
    Color chipColor;
    IconData iconData;

    switch (changeType) {
      case ChangeType.positive:
        chipColor = Colors.green;
        iconData = Icons.arrow_upward;
        break;
      case ChangeType.negative:
        chipColor = Colors.red;
        iconData = Icons.arrow_downward;
        break;
      case ChangeType.neutral:
        chipColor = Colors.grey;
        iconData = Icons.remove;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: chipColor.withOpacity(0.1),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            iconData,
            size: 16,
            color: chipColor,
          ),
          const SizedBox(width: 4),
          Text(
            change,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  fontWeight: FontWeight.w600,
                  color: chipColor,
                ),
          ),
        ],
      ),
    );
  }
}