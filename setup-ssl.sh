#!/bin/bash

# SSL Certificate Setup for search.cads.arda.or.th
# This script helps you set up SSL certificates for production

set -e

DOMAIN="search.cads.arda.or.th"
SSL_DIR="./ssl"
EMAIL="admin@arda.or.th"  # Change this to your email

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

echo "🔒 SSL Certificate Setup for $DOMAIN"
echo "====================================="

# Create SSL directory
mkdir -p "$SSL_DIR"
mkdir -p "$SSL_DIR/certbot"
mkdir -p "logs/nginx"

# Function to generate self-signed certificate for testing
generate_self_signed() {
    log_info "Generating self-signed certificate for testing..."
    
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$SSL_DIR/$DOMAIN.key" \
        -out "$SSL_DIR/$DOMAIN.crt" \
        -subj "/C=TH/ST=Bangkok/L=Bangkok/O=ARDA/OU=IT/CN=$DOMAIN"
    
    log_success "Self-signed certificate generated"
    log_warning "This is for testing only. Use Let's Encrypt for production."
}

# Function to set up Let's Encrypt
setup_letsencrypt() {
    log_info "Setting up Let's Encrypt certificate..."
    
    # Check if domain is accessible
    log_info "Checking if $DOMAIN is accessible..."
    if curl -s --connect-timeout 5 "http://$DOMAIN" > /dev/null 2>&1; then
        log_success "Domain is accessible"
    else
        log_warning "Domain may not be accessible yet. Proceeding anyway..."
    fi
    
    # Start nginx temporarily for Let's Encrypt challenge
    log_info "Starting temporary nginx for Let's Encrypt challenge..."
    
    # Create temporary nginx config for challenge
    cat > "$SSL_DIR/nginx-temp.conf" << EOF
events {
    worker_connections 1024;
}

http {
    server {
        listen 80;
        server_name $DOMAIN;
        
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        
        location / {
            return 200 'OK';
            add_header Content-Type text/plain;
        }
    }
}
EOF
    
    # Run certbot
    docker run --rm \
        -v "$PWD/$SSL_DIR/certbot:/etc/letsencrypt" \
        -v "$PWD/$SSL_DIR/certbot:/var/www/certbot" \
        -p 80:80 \
        certbot/certbot certonly \
        --standalone \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        -d "$DOMAIN"
    
    # Copy certificates to expected location
    if [ -f "$SSL_DIR/certbot/live/$DOMAIN/fullchain.pem" ]; then
        cp "$SSL_DIR/certbot/live/$DOMAIN/fullchain.pem" "$SSL_DIR/$DOMAIN.crt"
        cp "$SSL_DIR/certbot/live/$DOMAIN/privkey.pem" "$SSL_DIR/$DOMAIN.key"
        log_success "Let's Encrypt certificate installed"
    else
        log_error "Let's Encrypt certificate generation failed"
        log_info "Falling back to self-signed certificate"
        generate_self_signed
    fi
}

# Function to use existing certificate
use_existing_cert() {
    log_info "Using existing certificate..."
    
    if [ -f "$SSL_DIR/$DOMAIN.crt" ] && [ -f "$SSL_DIR/$DOMAIN.key" ]; then
        log_success "Existing certificate found"
        
        # Check certificate validity
        if openssl x509 -in "$SSL_DIR/$DOMAIN.crt" -noout -checkend 86400; then
            log_success "Certificate is valid for at least 24 hours"
        else
            log_warning "Certificate expires soon or is invalid"
        fi
    else
        log_error "Existing certificate not found"
        return 1
    fi
}

# Main menu
echo ""
echo "Choose SSL certificate setup method:"
echo "1) Use existing certificate (if you have one)"
echo "2) Generate self-signed certificate (for testing)"
echo "3) Set up Let's Encrypt certificate (for production)"
echo "4) Skip SSL setup (HTTP only - not recommended for production)"
echo ""

read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        if use_existing_cert; then
            log_success "Using existing certificate"
        else
            log_info "Falling back to self-signed certificate"
            generate_self_signed
        fi
        ;;
    2)
        generate_self_signed
        ;;
    3)
        setup_letsencrypt
        ;;
    4)
        log_warning "Skipping SSL setup - HTTP only mode"
        log_warning "This is not recommended for production!"
        ;;
    *)
        log_error "Invalid choice"
        exit 1
        ;;
esac

# Set proper permissions
if [ -f "$SSL_DIR/$DOMAIN.key" ]; then
    chmod 600 "$SSL_DIR/$DOMAIN.key"
    chmod 644 "$SSL_DIR/$DOMAIN.crt"
    log_success "SSL certificate permissions set"
fi

echo ""
log_success "SSL setup completed!"
echo ""
echo "Next steps:"
echo "1. Update your DNS to point $DOMAIN to this server"
echo "2. Configure your .env.production file"
echo "3. Run ./deploy-production.sh to start the service"
echo ""

# Show certificate info if available
if [ -f "$SSL_DIR/$DOMAIN.crt" ]; then
    echo "Certificate information:"
    openssl x509 -in "$SSL_DIR/$DOMAIN.crt" -noout -subject -dates
fi