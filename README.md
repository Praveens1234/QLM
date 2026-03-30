# QLM Mobile

A Flutter-based mobile application for QLM (Quantitative Learning Machine) - Professional trading and analysis platform.

## Features

### 📊 Dashboard
- Real-time portfolio overview
- Performance metrics and KPIs
- Interactive charts and graphs
- Recent activity feed

### 📈 Chart Viewer
- Professional trading charts with candlestick patterns
- Multiple timeframe support (1m, 5m, 15m, 1H, 4H, 1D, 1W, 1M)
- Technical indicators (RSI, MACD, MA, Bollinger, Volume)
- Zoom and pan functionality
- Fullscreen mode

### 🗃️ Data Manager
- Browse and manage datasets
- Upload new datasets
- Filter and search capabilities
- Data size and statistics
- Download datasets

### 🔬 Strategy Lab
- Code editor for creating trading strategies
- Syntax highlighting
- Multiple strategy tabs
- Parameter configuration
- Test and run strategies
- Console output

### 📊 Backtest Runner
- Configure backtests with custom parameters
- Progress tracking during backtest execution
- Performance metrics (Total Return, Sharpe Ratio, Max Drawdown, Win Rate)
- Equity curve visualization
- Trade history
- Export results

### 🔍 Data Inspector
- Browse detailed dataset information
- Search and filter data
- Pagination for large datasets
- Statistics and data quality metrics
- Export functionality

### 🔧 MCP Service
- Manage Model Context Protocol services
- Monitor service status
- Configure service endpoints
- View service logs
- Test service connections

### ⚙️ Settings
- Server connection management
- Theme selection (Light, Dark, System)
- Notification preferences
- Biometric authentication
- App information and support

## Server Connection

The app requires connection to a QLM server. On first launch, you'll be prompted to enter your server URL:

- Local development: `http://localhost:3000` or `http://127.0.0.1:3000`
- Network server: `http://192.168.x.x:3000`
- Production: `https://your-domain.com`

## Technical Details

### Architecture
- **Framework**: Flutter with Material You design (Material 3)
- **State Management**: Provider + ChangeNotifier
- **HTTP Client**: Dio and HTTP
- **Charts**: FL Chart
- **Storage**: SharedPreferences for settings

### Design System
- Material You dynamic theming
- Light & Dark themes
- 8-point grid system
- Custom color palette
- Professional typography (Inter font)

### CI/CD
Automated build and deployment using GitHub Actions:
- Runs on every push to `mobile-apk` branch
- Code analysis and linting
- Automated testing
- APK generation
- Artifact upload
- Automatic releases

## Getting Started

### Prerequisites
- Flutter SDK 3.16.0+
- Dart 3.0+
- Android SDK (for Android builds)

### Local Development
```bash
# Clone the repository
git clone https://github.com/Praveens1234/QLM.git
cd QLM/qlm_mobile

# Install dependencies
flutter pub get

# Run the app
flutter run
```

### Building APK
Since this project includes a CI/CD workflow, you don't need to build locally. GitHub Actions will automatically build the APK on every push.

To trigger a build manually:
1. Push your changes to the `mobile-apk` branch
2. GitHub Actions will automatically start the build
3. Download the APK from the Actions tab or Releases

### Local Build (Optional)
If you prefer to build locally:
```bash
flutter build apk --release
```

## Configuration

### Environment Variables
The app uses SharedPreferences for local configuration:
- `serverUrl`: QLM server URL
- `isConnected`: Connection status
- `themeMode`: Selected theme (light/dark/system)

### Adding New Screens
1. Create new screen file in `lib/screens/`
2. Import in `lib/screens/home_screen.dart`
3. Add navigation route in `lib/main.dart`
4. Add navigation button in `lib/widgets/bottom_nav_bar.dart`

## Testing

### Running Tests
```bash
flutter test
```

### Code Analysis
```bash
flutter analyze
```

### Formatting
```bash
dart format .
```

## Deployment

### GitHub Actions (Recommended)
The project includes a comprehensive GitHub Actions workflow that:
- Automatically builds APK on every push
- Runs tests and analysis
- Creates GitHub releases with APK
- Uploads artifacts

### Manual Deployment
To build and deploy manually:
1. Create a signed APK
2. Upload to your distribution platform
3. Update version in `pubspec.yaml`

## Troubleshooting

### Common Issues

**Build fails with asset errors**
Make sure to create placeholder files in assets directories or add actual assets before building.

**Connection fails**
- Verify the server URL format
- Check if the server is running
- Ensure CORS is configured on the server

**Test failures**
Some tests may fail due to missing assets. This is expected and won't prevent the APK from building.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is part of the QLM ecosystem. Please refer to the main QLM repository for license details.

## Support

For support and questions:
- Open an issue on GitHub
- Check the QLM documentation
- Contact the development team

## Version History

- **v1.0.0** - Initial mobile app release
  - Server connection management
  - Dashboard with metrics
  - Chart viewer with multiple timeframes
  - Data manager
  - Strategy lab
  - Backtest runner
  - Data inspector
  - MCP service management
  - Settings and configuration