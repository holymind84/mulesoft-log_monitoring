# Mulesoft Log Monitoring (CloudHub 1.0)

A Python application for monitoring Mulesoft CloudHub 1.0 applications logs across multiple workers and control planes with customizable pattern matching and email alerts.

## ⚠️ Important Note

This tool is specifically designed for applications deployed on CloudHub 1.0. It is not compatible with CloudHub 2.0 deployments due to different API endpoints and authentication mechanisms.

## Features

- 🔄 Multi-worker support
- 🌍 Multiple control planes (US, EU1, GOV)
- 🔍 Customizable pattern matching
- 📧 Email notifications
- 👥 Support for multiple applications monitoring
- 📊 Last check tracking per instance
- 🔒 Secure credential management
- 🐛 Optional verbose logging for debugging

## Prerequisites

- Python 3.8+
- Access to Mulesoft Anypoint Platform
- Applications deployed on CloudHub 1.0 (not compatible with CloudHub 2.0)
- SMTP server for email notifications

## Installation

1. Clone the repository:
```bash
git clone https://github.com/holymind84/mulesoft-log_monitoring.git
cd mulesoft-log_monitoring
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

### Environment Variables

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Configure the following variables:
```env
# Mulesoft Configuration
MULESOFT_CLIENT_ID=your-client-id
MULESOFT_CLIENT_SECRET=your-client-secret
MULESOFT_ORG_ID=your-org-id
MULESOFT_ENV_ID=your-env-id
MULESOFT_CONTROL_PLANE=us  # or eu1, gov

# Monitoring Configuration
CHECK_INTERVAL_SECONDS=300

# SMTP Configuration
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
SMTP_SENDER=alerts@example.com

# Debug Configuration
VERBOSE_LOGGING=false  # Set to true for detailed logging
```

### Pattern Configuration

Create a `patterns.json` file from the example:
```bash
cp patterns.example.json patterns.json
```

Configure your patterns:
```json
[
  {
    "type": "Error",
    "search_string": "Critical error",
    "mail": ["admin@example.com"],
    "app_name": "your-mule-app-name"
  },
  {
    "type": "Warning",
    "search_string": "High CPU usage",
    "mail": ["ops@example.com", "admin@example.com"],
    "app_name": "another-mule-app"
  }
]
```

## Usage

Start the monitoring service:
```bash
python log_monitor.py
```

The application will:
1. Monitor all configured applications on CloudHub 1.0
2. Check all workers of each application
3. Send email alerts when patterns are matched
4. Track the last check time per instance

### Debug Mode

To enable verbose logging for debugging:
1. Set `VERBOSE_LOGGING=true` in your `.env` file
2. Or set it temporarily: `VERBOSE_LOGGING=true python log_monitor.py`

Verbose logging includes:
- API endpoint details
- Request headers
- Response data
- Error details and stack traces

## Project Structure

```
mulesoft-log_monitoring/
├── log_monitor.py        # Main application
├── patterns.example.json # Example pattern configuration
├── .env.example         # Example environment variables
├── requirements.txt     # Python dependencies
├── last_check/         # Directory for tracking last checks
├── .gitignore          # Git ignore file
├── README.md           # This file
└── LICENSE             # MIT License
```

## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Support

For support, please:
1. Check existing issues or create a new one: https://github.com/holymind84/mulesoft-log_monitoring/issues
2. Fork the repository and create a pull request with your fix
3. Contact the project maintainers

## Donations

If you find this project helpful, consider supporting its development:

[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/SBernardini84)

Supporting this project helps:
- 🚀 Maintain and improve the codebase
- 💡 Develop new features
- 🐛 Provide faster bug fixes
- 📚 Keep documentation up-to-date

*Your support is greatly appreciated and helps keep this project actively maintained!*

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
