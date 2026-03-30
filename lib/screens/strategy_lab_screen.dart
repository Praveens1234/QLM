import 'package:flutter/material.dart';
import '../themes/app_theme.dart';

class StrategyLabScreen extends StatefulWidget {
  const StrategyLabScreen({super.key});

  @override
  State<StrategyLabScreen> createState() => _StrategyLabScreenState();
}

class _StrategyLabScreenState extends State<StrategyLabScreen> {
  int _currentIndex = 0;
  final List<StrategyTab> _tabs = [
    StrategyTab(
      name: 'Moving Average',
      code: '''class MovingAverageStrategy {
  constructor() {
    this.shortMA = 20;
    this.longMA = 50;
  }

  onData(data) {
    if (data.close < this.shortMA) {
      return { action: 'BUY', amount: 1 };
    }
    if (data.close > this.longMA) {
      return { action: 'SELL', amount: 1 };
    }
    return null;
  }
}''',
    ),
    StrategyTab(
      name: 'RSI Strategy',
      code: '''class RsiStrategy {
  constructor() {
    this.rsiPeriod = 14;
    this.overbought = 70;
    this.oversold = 30;
  }

  onData(data) {
    const rsi = this.calculateRSI(data, this.rsiPeriod);
    if (rsi < this.oversold) {
      return { action: 'BUY', amount: 1 };
    }
    if (rsi > this.overbought) {
      return { action: 'SELL', amount: 1 };
    }
    return null;
  }

  calculateRSI(data, period) {
    // RSI calculation logic
    return 50;
  }
}''',
    ),
    StrategyTab(
      name: 'MACD',
      code: '''class MacdStrategy {
  constructor() {
    this.fastLength = 12;
    this.slowLength = 26;
    this.signalLength = 9;
  }

  onData(data) {
    const macd = this.calculateMACD(data);
    const signal = this.calculateSignal(macd);

    if (macd > signal) {
      return { action: 'BUY', amount: 1 };
    }
    if (macd < signal) {
      return { action: 'SELL', amount: 1 };
    }
    return null;
  }

  calculateMACD(data) {
    // MACD calculation logic
    return 0;
  }
}''',
    ),
  ];

  void _addNewStrategy() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('New Strategy'),
        content: TextField(
          decoration: const InputDecoration(
            labelText: 'Strategy Name',
            hintText: 'My Awesome Strategy',
          ),
          autofocus: true,
          onSubmitted: (value) {
            if (value.isNotEmpty) {
              setState(() {
                _tabs.add(StrategyTab(
                  name: value,
                  code: '''class ${value.replaceAll(' ', '')} {
  constructor() {
    // Initialize parameters
  }

  onData(data) {
    // Your trading logic here
    return null;
  }
}''',
                ));
              });
              Navigator.pop(context);
            }
          },
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () {
              // Create strategy with default name
            },
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }

  void _closeTab(int index) {
    setState(() {
      _tabs.removeAt(index);
      if (_currentIndex >= _tabs.length) {
        _currentIndex = _tabs.length - 1;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Strategy Lab'),
        actions: [
          IconButton(
            icon: const Icon(Icons.play_arrow_rounded),
            onPressed: () => _runStrategy(context),
            tooltip: 'Run Strategy',
          ),
          IconButton(
            icon: const Icon(Icons.save_rounded),
            onPressed: () => _saveStrategy(context),
            tooltip: 'Save Strategy',
          ),
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            onPressed: () => _showParameters(context),
            tooltip: 'Parameters',
          ),
        ],
      ),
      body: Column(
        children: [
          // Tabs
          Container(
            height: 48,
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(color: Theme.of(context).dividerColor),
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: ListView.builder(
                    scrollDirection: Axis.horizontal,
                    itemCount: _tabs.length,
                    itemBuilder: (context, index) {
                      return _buildTab(context, index);
                    },
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.add),
                  onPressed: _addNewStrategy,
                  tooltip: 'Add Strategy',
                ),
              ],
            ),
          ),
          // Code Editor
          Expanded(
            child: _buildCodeEditor(context, _currentIndex),
          ),
          // Bottom toolbar
          _buildBottomToolbar(context),
        ],
      ),
    );
  }

  Widget _buildTab(BuildContext context, int index) {
    final isActive = index == _currentIndex;
    return GestureDetector(
      onTap: () {
        setState(() {
          _currentIndex = index;
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: isActive ? Theme.of(context).colorScheme.primary : Colors.transparent,
              width: 3,
            ),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _tabs[index].name,
              style: Theme.of(context).textTheme.labelMedium?.copyWith(
                    fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                    color: isActive
                        ? Theme.of(context).colorScheme.primary
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
            if (_tabs.length > 1)
              IconButton(
                icon: Icon(Icons.close, size: 16),
                onPressed: () => _closeTab(index),
                constraints: BoxConstraints.tight(const Size(24, 24)),
                padding: EdgeInsets.zero,
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildCodeEditor(BuildContext context, int index) {
    return Container(
      padding: const EdgeInsets.all(16),
      child: TextField(
        controller: TextEditingController(text: _tabs[index].code)
          ..selection = TextSelection.collapsed(offset: _tabs[index].code.length),
        maxLines: null,
        expands: true,
        style: const TextStyle(
          fontFamily: 'JetBrainsMono',
          fontSize: 14,
          height: 1.5,
        ),
        decoration: InputDecoration(
          border: InputBorder.none,
          hintText: '// Write your strategy here',
        ),
        onChanged: (value) {
          _tabs[index].code = value;
        },
      ),
    );
  }

  Widget _buildBottomToolbar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: Theme.of(context).dividerColor),
        ),
      ),
      child: Row(
        children: [
          _buildStatusIndicator(context),
          const Spacer(),
          TextButton.icon(
            onPressed: _showConsole,
            icon: const Icon(Icons.terminal_rounded, size: 18),
            label: const Text('Console'),
          ),
          const SizedBox(width: 16),
          ElevatedButton.icon(
            onPressed: () => _runStrategy(context),
            icon: const Icon(Icons.play_arrow_rounded),
            label: const Text('Test Run'),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIndicator(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: Colors.green,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Ready',
          style: Theme.of(context).textTheme.labelMedium?.copyWith(
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
        ),
      ],
    );
  }

  void _runStrategy(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Running strategy...')),
    );
  }

  void _saveStrategy(BuildContext context) {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Strategy saved')),
    );
  }

  void _showParameters(BuildContext context) {
    showModalBottomSheet(
      context: context,
      builder: (context) => Container(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Strategy Parameters',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: InputDecoration(
                labelText: 'Initial Capital',
                hintText: '10000',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            TextField(
              decoration: InputDecoration(
                labelText: 'Position Size',
                hintText: '1',
              ),
              keyboardType: TextInputType.number,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Apply'),
            ),
          ],
        ),
      ),
    );
  }

  void _showConsole() {
    // TODO: Implement console view
  }
}

class StrategyTab {
  String name;
  String code;

  StrategyTab({required this.name, required this.code});
}