# QLTY Framework

Mobile automation testing framework for iOS and Android platforms.

## Documentation

For complete documentation and usage guides, please visit the project documentation site.

## Installation

### Quick Install (Remote)

Install QLTY Framework along with your client test repository:

```bash
# Using HTTPS
curl -fsSL https://raw.githubusercontent.com/qltyautomation/QLTYFramework/main/install.sh | bash -s -- --repo https://github.com/your-org/your-tests.git

# Using SSH (recommended for SSH key authentication)
curl -fsSL https://raw.githubusercontent.com/qltyautomation/QLTYFramework/main/install.sh | bash -s -- --repo https://bitbucket.org/your-org/your-tests.git --ssh

# With automatic ChromeDriver installation
curl -fsSL https://raw.githubusercontent.com/qltyautomation/QLTYFramework/main/install.sh | bash -s -- --repo https://bitbucket.org/your-org/your-tests.git --ssh --chromedriver
```

### Install Options

| Option | Description |
|--------|-------------|
| `--repo URL` | Client test repository URL (required) |
| `--ssh` | Use SSH for client repo clone (converts HTTPS URL to SSH) |
| `--chromedriver` | Auto-download matching ChromeDriver for installed Chrome |
| `--framework URL` | Custom framework repository URL |
| `--install-dir DIR` | Custom installation directory (default: ~/QLTYAutomation) |

### Manual Install

```bash
pip install -e /path/to/QLTYFramework
```

## Quick Start

QLTY Framework provides a comprehensive testing solution for mobile applications using Appium.

## Features

- Cross-platform mobile testing (iOS & Android)
- Appium-based automation
- Integration with CI/CD pipelines
- Extensive reporting capabilities
- Cloud testing platform support

## License

MIT License
