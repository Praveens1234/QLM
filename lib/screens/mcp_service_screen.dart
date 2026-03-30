import 'package:flutter/material.dart';
import '../themes/app_theme.dart';

class McpServiceScreen extends StatefulWidget {
  const McpServiceScreen({super.key});

  @override
  State<McpServiceScreen> createState() => _McpServiceScreenState();
}

class _McpServiceScreenState extends State<McpServiceScreen> {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          children: [
            Icon(Icons.memory, color: Theme.of(context).colorScheme.primary),
            const SizedBox(width: 12),
            const Text('MCP Services'),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () => _refreshServices(context),
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildServicesList(context),
          const SizedBox(height: 24),
          _buildAddServiceButton(context),
        ],
      ),
    );
  }

  Widget _buildServicesList(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Active Services',
          style: Theme.of(context).textTheme.titleLarge?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
        const SizedBox(height: 16),
        ListView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          itemCount: 3,
          itemBuilder: (context, index) {
            return _buildServiceCard(
              context,
              index: index,
              title: ['Market Data API', 'Analytics Engine', 'Notification Service'][index],
              subtitle: ['API', 'Engine', 'Service'][index],
              status: ['active', 'error', 'stopped'][index],
              endpoint: 'http://localhost:3000/service/${index + 1}',
            );
          },
        ),
      ],
    );
  }

  Widget _buildServiceCard(
    BuildContext context, {
    required int index,
    required String title,
    required String subtitle,
    required String status,
    required String endpoint,
  }) {
    Color statusColor;
    IconData statusIcon;

    switch (status) {
      case 'active':
        statusColor = Colors.green;
        statusIcon = Icons.check_circle_rounded;
        break;
      case 'error':
        statusColor = Colors.red;
        statusIcon = Icons.error_rounded;
        break;
      default:
        statusColor = Colors.grey;
        statusIcon = Icons.pause_circle_rounded;
    }

    return Card(
      elevation: 0,
      child: ExpansionTile(
        leading: CircleAvatar(
          backgroundColor: statusColor,
          child: Icon(statusIcon, color: Colors.white, size: 20),
        ),
        title: Text(title, style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold)),
        subtitle: Text('$subtitle • $status'),
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Endpoint',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 8),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceVariant,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: SelectableText(
                    endpoint,
                    style: const TextStyle(fontFamily: 'JetBrainsMono'),
                  ),
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  children: [
                    ElevatedButton.icon(
                      onPressed: () => _testService(context, title),
                      icon: const Icon(Icons.play_arrow),
                      label: const Text('Test'),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => _viewLogs(context, title),
                      icon: const Icon(Icons.list),
                      label: const Text('Logs'),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAddServiceButton(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: () => _showAddServiceDialog(context),
      icon: const Icon(Icons.add),
      label: const Text('Add New Service'),
      style: ElevatedButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
      ),
    );
  }

  void _testService(BuildContext context, String serviceName) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Testing $serviceName...'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  void _viewLogs(BuildContext context, String serviceName) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('$serviceName Logs'),
        content: const Text('Log viewer coming soon'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _refreshServices(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Refreshing services...')),
    );
  }

  void _showAddServiceDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Add Service'),
        content: const Text('Service configuration coming soon'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }
}