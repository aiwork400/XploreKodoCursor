# Environment Setup Guide

## Quick Start

1. **Copy the example environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your actual values:**
   - Database connection string
   - API keys for payment gateways
   - Notification service credentials
   - Translation API keys (if using)

3. **Verify `.env` is in `.gitignore`:**
   - The `.env` file should NEVER be committed to git
   - Only `.env.example` should be tracked

## Required Environment Variables

### Database
- `DATABASE_URL` - PostgreSQL connection string

### Payment Gateways
- `STRIPE_API_KEY` - Stripe API key
- `PAYPAL_CLIENT_ID` - PayPal Client ID
- `PAYPAL_SECRET` - PayPal Secret

### Notifications
- `SENDGRID_API_KEY` - SendGrid API key for emails
- `TWILIO_ACCOUNT_SID` - Twilio Account SID
- `TWILIO_AUTH_TOKEN` - Twilio Auth Token
- `TWILIO_PHONE_NUMBER` - Twilio phone number

### Translation (Optional)
- `TRANSLATION_API_KEY` - Translation service API key
- `TRANSLATION_API_URL` - Translation service URL

### Application
- `PHASE_2_ENABLED` - Set to "True" to enable Phase 2 features
- `DEBUG` - Set to "True" for debug mode
- `SECRET_KEY` - Secret key for application security

## Security Notes

- Never commit `.env` files to version control
- Use different keys for development and production
- Rotate API keys regularly
- Use the SecurityAuditTool to check for exposed secrets

