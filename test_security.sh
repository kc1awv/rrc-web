#!/bin/bash
# Security feature testing helper

echo "======================================================================"
echo "RRC Web Security Feature Test"
echo "======================================================================"
echo ""

# Check if config exists
CONFIG_PATH="$HOME/.rrc-web/config.json"
if [ ! -f "$CONFIG_PATH" ]; then
    echo "   Config file not found at $CONFIG_PATH"
    echo "   Run 'rrc-web' first to generate default config"
    exit 1
fi

echo "   Config file found: $CONFIG_PATH"
echo ""

# Check authentication settings
echo "--------------------------------"
echo "Authentication Configuration"
echo "--------------------------------"
AUTH_ENABLED=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('enable_auth', False))" 2>/dev/null)
if [ "$AUTH_ENABLED" = "True" ]; then
    echo "   Authentication: ENABLED"
    AUTH_TOKEN=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('auth_token', ''))" 2>/dev/null)
    if [ -n "$AUTH_TOKEN" ]; then
        echo "   Auth token: Configured (${#AUTH_TOKEN} characters)"
    else
        echo "   Auth token: NOT SET (authentication will not work!)"
    fi
else
    echo "   Authentication: DISABLED"
fi
echo ""

# Check SSL settings
echo "--------------------------------"
echo "SSL/TLS Configuration"
echo "--------------------------------"
SSL_ENABLED=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('enable_ssl', False))" 2>/dev/null)
if [ "$SSL_ENABLED" = "True" ]; then
    echo "   SSL/TLS: ENABLED"
    
    CERT_PATH=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('ssl_cert_path', ''))" 2>/dev/null)
    KEY_PATH=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('ssl_key_path', ''))" 2>/dev/null)
    
    # Expand ~ in paths
    CERT_PATH="${CERT_PATH/#\~/$HOME}"
    KEY_PATH="${KEY_PATH/#\~/$HOME}"
    
    if [ -f "$CERT_PATH" ]; then
        echo "   Certificate: Found at $CERT_PATH"
        # Check certificate expiry
        EXPIRY=$(openssl x509 -in "$CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2)
        if [ -n "$EXPIRY" ]; then
            echo "   Expires: $EXPIRY"
        fi
    else
        echo "   Certificate: NOT FOUND at $CERT_PATH"
        echo "   Run 'python -m rrc_web.generate_cert' to create"
    fi
    
    if [ -f "$KEY_PATH" ]; then
        echo "   Private key: Found at $KEY_PATH"
        # Check permissions
        PERMS=$(stat -c "%a" "$KEY_PATH" 2>/dev/null || stat -f "%Lp" "$KEY_PATH" 2>/dev/null)
        if [ "$PERMS" = "600" ] || [ "$PERMS" = "400" ]; then
            echo "   Permissions: Secure ($PERMS)"
        else
            echo "   Permissions: $PERMS (recommend 600)"
        fi
    else
        echo "   Private key: NOT FOUND at $KEY_PATH"
        echo "   Run 'python -m rrc_web.generate_cert' to create"
    fi
else
    echo "   SSL/TLS: DISABLED"
fi
echo ""

# Check security headers
echo "--------------------------------"
echo "Security Headers"
echo "--------------------------------"
HEADERS_ENABLED=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('enable_security_headers', True))" 2>/dev/null)
if [ "$HEADERS_ENABLED" = "True" ]; then
    echo "   Security headers: ENABLED"
else
    echo "   Security headers: DISABLED (not recommended)"
fi
echo ""

# Check session settings
echo "--------------------------------"
echo "Session Configuration"
echo "--------------------------------"
SESSION_TIMEOUT=$(python3 -c "import json; print(json.load(open('$CONFIG_PATH')).get('session_timeout_minutes', 60))" 2>/dev/null)
echo "Session timeout: $SESSION_TIMEOUT minutes"
echo ""

# Check allowed origins
echo "--------------------------------"
echo "CORS Configuration"
echo "--------------------------------"
ORIGINS=$(python3 -c "import json; origins = json.load(open('$CONFIG_PATH')).get('allowed_origins', []); print(', '.join(origins) if origins else 'None configured')" 2>/dev/null)
echo "Allowed origins: $ORIGINS"
echo ""

# Summary
echo "--------------------------------"
echo "Security Summary"
echo "--------------------------------"

SECURITY_SCORE=0
MAX_SCORE=3

if [ "$AUTH_ENABLED" = "True" ] && [ -n "$AUTH_TOKEN" ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "   Authentication is properly configured"
else
    echo "   Authentication is not enabled or configured"
fi

if [ "$SSL_ENABLED" = "True" ] && [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "   SSL/TLS is properly configured"
else
    echo "   SSL/TLS is not enabled or certificates are missing"
fi

if [ "$HEADERS_ENABLED" = "True" ]; then
    SECURITY_SCORE=$((SECURITY_SCORE + 1))
    echo "   Security headers are enabled"
else
    echo "   Security headers are disabled"
fi

echo ""
echo "Security Score: $SECURITY_SCORE/$MAX_SCORE"

if [ $SECURITY_SCORE -eq 3 ]; then
    echo "   Excellent! All security features are enabled and configured."
elif [ $SECURITY_SCORE -eq 2 ]; then
    echo "   Good! Most security features are enabled."
elif [ $SECURITY_SCORE -eq 1 ]; then
    echo "   Fair. Consider enabling more security features."
else
    echo "   No security features enabled. Consider running 'rrc-security-setup'."
fi

echo ""
echo "To enable security features, run: python -m rrc_web.setup_security"
echo ""
