"""
Diagnose PostgreSQL connection issues.
This script helps identify what might be wrong with the connection.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path, override=False)

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    print("[ERROR] DATABASE_URL not found in .env file")
    sys.exit(1)

# Parse the database URL
parsed = urlparse(DATABASE_URL)
db_user = parsed.username
db_password = parsed.password
db_host = parsed.hostname
db_port = parsed.port or 5432
db_name = parsed.path.lstrip('/')

print("=" * 60)
print("PostgreSQL Connection Diagnostics")
print("=" * 60)
print()
print(f"Connection Details (from .env file):")
print(f"  Host: {db_host}")
print(f"  Port: {db_port}")
print(f"  Database: {db_name}")
print(f"  User: {db_user}")
print(f"  Password Length: {len(db_password) if db_password else 0} characters")
print(f"  Password Contains Special Chars: {any(c in db_password for c in '@#$%^&*()[]{}|\\:;"\'<>?,./') if db_password else False}")
print()

# Check for common issues
print("Checking for common issues...")
print()

issues_found = []

if not db_password:
    issues_found.append("Password is empty")
elif db_password == "YOUR_POSTGRES_PASSWORD":
    issues_found.append("Password is still the placeholder value")

if '@' in db_password or '#' in db_password or '%' in db_password:
    issues_found.append("Password contains special characters that might need URL encoding")

if db_name == "":
    issues_found.append("Database name is empty")

if issues_found:
    print("[WARNINGS] Potential issues found:")
    for issue in issues_found:
        print(f"  - {issue}")
    print()

# Provide guidance
print("=" * 60)
print("Troubleshooting Steps:")
print("=" * 60)
print()
print("1. Verify your PostgreSQL password:")
print("   - Open pgAdmin or psql")
print("   - Try connecting with the same username and password")
print("   - If it fails there too, the password is incorrect")
print()
print("2. If password contains special characters (@, #, %, etc.):")
print("   - URL-encode them in the DATABASE_URL")
print("   - Example: @ becomes %40, # becomes %23, % becomes %25")
print()
print("3. Test connection manually:")
print("   - Open Command Prompt or PowerShell")
print("   - Run: psql -U postgres -h localhost -p 5432")
print("   - Enter your password when prompted")
print()
print("4. Check if PostgreSQL is running:")
print("   - Windows: Open Services (services.msc)")
print("   - Look for 'postgresql' service and ensure it's running")
print()
print("5. Reset PostgreSQL password (if needed):")
print("   - Open pgAdmin")
print("   - Right-click on 'Login/Group Roles' -> 'postgres' -> Properties")
print("   - Go to 'Definition' tab and set a new password")
print("   - Update your .env file with the new password")
print()
print("=" * 60)
print("Current DATABASE_URL (for reference):")
print("=" * 60)
# Show URL with password masked
masked_url = DATABASE_URL
if db_password:
    masked_url = DATABASE_URL.replace(db_password, "*" * len(db_password))
print(masked_url)
print()

