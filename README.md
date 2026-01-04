# RRC Web Client

A web-based client for **RRC (Reticulum Relay Chat)**

RRC Web provides a browser interface to connect
[rrcd](https://github.com/kc1awv/rrcd) chat hubs over the
[Reticulum Network](https://reticulum.network), enabling group communication
without relying on traditional internet infrastructure.

## Features

- **Browser-based Interface** - Access RRC from any modern web browser
- **Multi-User Chat** - Communicate with multiple users in real-time
- **Multi-room Chat** - Join and participate in multiple chat rooms
- **Hub Discovery** - Automatically discover RRC hubs on the network
- **Modern UI** - Responsive interface built with Svelte and daisyUI
- **WebSocket Backend** - Real-time communication between browser and
   Reticulum network
- **Security Features** - Optional authentication and SSL/TLS support
- **Security Headers** - Built-in protection against common web vulnerabilities

## Architecture

RRC Web consists of two main components:

1. **Python Backend** (`rrc_web/`) - Bridges WebSocket connections to the
    Reticulum network
2. **Svelte Frontend** (`svelte-frontend/`) - Web UI for chat interaction

The backend runs a local HTTP/WebSocket server that your browser connects to,
while maintaining connections to RRC hubs over the Reticulum network. You can,
for example, run the backend on a Raspberry Pi connected to Reticulum, and
access the frontend from any device on your local network.

## Prerequisites

- **Python 3.11 or higher**
- **Node.js 16 or higher** (only needed if rebuilding the frontend)
- **Reticulum** - Installed and configured on your system

## Installation

### Quick Install

```bash
# Clone the repository
git clone https://github.com/kc1awv/rrc-web.git
cd rrc-web

# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`

# Install the package
pip install .

# Or for development
pip install -e ".[dev]"
```

### Configuration

Configuration is done via a JSON file. You can start the client and it will
generate a default config file at `~/.rrc-web/config.json`. You can also copy
the provided `config.example.json` to that location and edit it as needed.

## Usage

### Starting the Client

```bash
# Using the installed command
rrc-web

# Or using the helper script
./run.sh

# With custom port
./run.sh --port 8080

# With debug logging
./run.sh --debug
```

The web interface will automatically open in your default browser at
`http://localhost:8080`.

### Command Line Options (run.sh)

```bash
Options:
  -p, --port PORT       Set the server port (default: 8080)
  -c, --config FILE     Use alternate config file
  -d, --debug           Enable debug logging
  -v, --verbose         Enable verbose logging
  -h, --help            Show help message
```

### Environment Variables

- `RRC_WEB_PORT` - Override server port
- `RRC_WEB_CONFIG` - Override config file path
- `RRC_LOG_LEVEL` - Set logging level (DEBUG, INFO, WARNING, ERROR)

## Connecting to a Hub

1. Start the RRC Web Client
2. Enter the hub destination hash (if not in config)
3. Choose a nickname (if not in config)
4. Click "Connect"
5. Join rooms and start chatting!

## Development

### Running Tests (if available)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=rrc_web tests/

# Run specific test file
pytest tests/test_backend.py
```

### Building the Frontend

If you need to modify the frontend:

```bash
cd svelte-frontend

# Install dependencies
npm install

# Build for production
npm run build

# Or use the build script
./build.sh
```

The built files will be output to `rrc_web/static-svelte/`.

### Code Formatting

```bash
# Format code with black
black rrc_web/

# Check with ruff
ruff check rrc_web/

# Type checking with mypy
mypy rrc_web/
```

## Configuration Options

| Option                    | Type        | Description                                  |
| ------------------------- | ----------- | -------------------------------------------- |
| `identity_path`           | string      | Path to Reticulum identity file              |
| `dest_name`               | string      | Reticulum destination name (e.g., "rrc.hub") |
| `hub_hash`                | string      | Hub destination hash (hex string)            |
| `nickname`                | string      | Your display nickname                        |
| `configdir`               | string/null | Reticulum config directory (null = default)  |
| `server_port`             | number      | HTTP server port                             |
| `server_host`             | string      | HTTP server host ("localhost" or "0.0.0.0")  |
| `auto_join_room`          | string      | Room to auto-join after connecting           |
| `theme`                   | string      | UI theme (currently only "dark")             |
| `enable_auth`             | boolean     | Enable authentication (requires auth_token)  |
| `auth_token`              | string      | Authentication token for login               |
| `enable_ssl`              | boolean     | Enable SSL/TLS (HTTPS and WSS)               |
| `ssl_cert_path`           | string      | Path to SSL certificate file                 |
| `ssl_key_path`            | string      | Path to SSL private key file                 |
| `session_timeout_minutes` | number      | Session timeout in minutes (default: 60)     |
| `allowed_origins`         | array       | Allowed CORS origins                         |
| `enable_security_headers` | boolean     | Enable security headers (recommended)        |

## Security Features

RRC Web includes optional security features designed for deployments where the
web interface may be accessible to others on the local network.

### Quick Security Setup

The easiest way to set up security features is using the interactive setup
script:


```bash
python -m rrc_web.setup_security
```

This will guide you through enabling authentication and SSL/TLS with sensible
defaults.

You can verify your security configuration at any time:


```bash
./test_security.sh
```

### Authentication

To enable authentication:

1. **Generate an authentication token:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update your `config.json`:**
   ```json
   {
     "enable_auth": true,
     "auth_token": "your-generated-token-here"
   }
   ```

3. **Restart the application.** Users will be prompted to enter the token before
    accessing the interface.

### SSL/TLS (HTTPS)

To enable SSL/TLS for encrypted connections:

1. **Generate a self-signed certificate:**
   ```bash
   python -m rrc_web.generate_cert
   ```

   Or with custom options:
   ```bash
   python -m rrc_web.generate_cert --hostname myhost --days 730
   ```

2. **Update your `config.json`:**
   ```json
   {
     "enable_ssl": true,
     "ssl_cert_path": "~/.rrc-web/cert.pem",
     "ssl_key_path": "~/.rrc-web/key.pem"
   }
   ```

3. **Restart the application.** The server will now run on HTTPS.

4. **Accept the self-signed certificate** in your browser (you'll see a security
    warning - this is expected for self-signed certificates).

### Combined Authentication and SSL

For maximum security, enable both:

```json
{
  "enable_auth": true,
  "auth_token": "your-token-here",
  "enable_ssl": true,
  "ssl_cert_path": "~/.rrc-web/cert.pem",
  "ssl_key_path": "~/.rrc-web/key.pem",
  "session_timeout_minutes": 60,
  "allowed_origins": ["https://localhost:8080"]
}
```

### Security Best Practices

- **Keep your auth token secret** - Don't share it or commit it to version
   control
- **Use strong tokens** - Always generate tokens using cryptographically secure
   methods
- **Limit network exposure** - Use `"server_host": "localhost"` unless you need
   remote access (for example, running on a Raspberry Pi and accessing the web
   interface from another device)
- **Regular token rotation** - Periodically generate new auth tokens
- **HTTPS for remote access** - Always enable SSL when accessing from other
   devices
- **Session timeout** - Set an appropriate session timeout for your use case
- **Monitor access** - Check logs for unauthorized access attempts

### Security Headers

By default, RRC Web includes security headers to protect against common
vulnerabilities:

- **Content Security Policy (CSP)** - Prevents XSS attacks
- **X-Frame-Options** - Prevents clickjacking
- **X-Content-Type-Options** - Prevents MIME-type sniffing
- **Referrer-Policy** - Controls referrer information
- **Permissions-Policy** - Restricts browser features

These can be disabled if needed by setting `"enable_security_headers": false` in
your config.

## Troubleshooting

### Connection Issues

- Ensure Reticulum is properly configured and running
- Verify the hub hash is correct
- Check that your Reticulum interface is connected

### Port Already in Use

If port 8080 is already in use:
```bash
./run.sh --port 8081
```

Or set in config:
```json
{
  "server_port": 8081
}
```

### Browser Not Opening

Manually navigate to `http://localhost:8080` in your browser.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## Links

- **Homepage**: https://github.com/kc1awv/rrc-web
- **Issues**: https://github.com/kc1awv/rrc-web/issues
- **rrcd**: https://github.com/kc1awv/rrcd
- **Reticulum Network**: https://reticulum.network

---

**Note:** RRC Web is in active development (Alpha). Expect changes and
    improvements.
