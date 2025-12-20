"""
Check PostgreSQL connection and database status.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dotenv import load_dotenv
import psycopg2
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

print(f"[INFO] Checking PostgreSQL connection...")
print(f"  Host: {db_host}")
print(f"  Port: {db_port}")
print(f"  User: {db_user}")
print()

# Step 1: Try connecting to PostgreSQL server (without specifying database)
print("[STEP 1] Testing connection to PostgreSQL server...")
try:
    conn = psycopg2.connect(
        host=db_host,
        port=db_port,
        database="postgres",  # Connect to default 'postgres' database first
        user=db_user,
        password=db_password
    )
    print("[SUCCESS] Connected to PostgreSQL server!")
    
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()[0]
    print(f"[INFO] PostgreSQL version: {version.split(',')[0]}")
    
    # Step 2: Check if the target database exists
    print(f"\n[STEP 2] Checking if database '{db_name}' exists...")
    cursor.execute("""
        SELECT datname FROM pg_database WHERE datname = %s;
    """, (db_name,))
    
    if cursor.fetchone():
        print(f"[SUCCESS] Database '{db_name}' exists!")
    else:
        print(f"[WARNING] Database '{db_name}' does not exist.")
        cursor.close()
        conn.close()
        
        # Note: CREATE DATABASE cannot be run in a transaction
        # Need to close current connection and create a new one with autocommit
        print(f"[INFO] Creating database '{db_name}'...")
        try:
            conn_autocommit = psycopg2.connect(
                host=db_host,
                port=db_port,
                database="postgres",
                user=db_user,
                password=db_password
            )
            conn_autocommit.autocommit = True
            cursor_autocommit = conn_autocommit.cursor()
            cursor_autocommit.execute(f'CREATE DATABASE "{db_name}";')
            cursor_autocommit.close()
            conn_autocommit.close()
            print(f"[SUCCESS] Database '{db_name}' created!")
        except Exception as e:
            print(f"[ERROR] Failed to create database: {e}")
            sys.exit(1)
    
    cursor.close()
    conn.close()
    
    # Step 3: Try connecting to the target database
    print(f"\n[STEP 3] Testing connection to database '{db_name}'...")
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        print(f"[SUCCESS] Connected to database '{db_name}' successfully!")
        conn.close()
        print("\n[SUCCESS] All checks passed! You can now run init_database.py")
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Cannot connect to database '{db_name}': {e}")
        sys.exit(1)
    
except psycopg2.OperationalError as e:
    error_msg = str(e)
    if "password authentication failed" in error_msg:
        print("[ERROR] Password authentication failed!")
        print("\nPossible issues:")
        print("  1. The password in DATABASE_URL is incorrect")
        print("  2. PostgreSQL authentication method may need adjustment")
        print("  3. The user may not have permission")
        print("\nTo reset PostgreSQL password, you can:")
        print("  - Use pgAdmin or psql to change the password")
        print("  - Or edit pg_hba.conf to allow local connections")
    elif "could not connect" in error_msg or "connection refused" in error_msg:
        print("[ERROR] Cannot connect to PostgreSQL server!")
        print("\nPossible issues:")
        print("  1. PostgreSQL is not running")
        print("  2. PostgreSQL is not listening on port", db_port)
        print("  3. Firewall is blocking the connection")
        print("\nTo start PostgreSQL on Windows:")
        print("  - Check Services (services.msc) for 'postgresql' service")
        print("  - Or use: net start postgresql-x64-XX (replace XX with version)")
    else:
        print(f"[ERROR] Connection error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
    sys.exit(1)

