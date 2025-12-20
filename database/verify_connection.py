"""
Verify PostgreSQL database connection.
This script helps diagnose connection issues before running init_database.py
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
    print("Please set DATABASE_URL in your .env file")
    sys.exit(1)

# Parse the database URL
try:
    parsed = urlparse(DATABASE_URL)
    db_user = parsed.username
    db_password = parsed.password
    db_host = parsed.hostname
    db_port = parsed.port or 5432
    db_name = parsed.path.lstrip('/')
    
    print(f"[INFO] Attempting to connect to PostgreSQL...")
    print(f"  Host: {db_host}")
    print(f"  Port: {db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    print(f"  Password: {'*' * len(db_password) if db_password else '[NOT SET]'}")
    print()
    
    # Check if password is still a placeholder
    if not db_password or db_password == "YOUR_POSTGRES_PASSWORD":
        print("[ERROR] Password is still a placeholder!")
        print("Please update DATABASE_URL in your .env file with your actual PostgreSQL password")
        sys.exit(1)
    
    # Try to connect
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        )
        print("[SUCCESS] Connected to PostgreSQL successfully!")
        
        # Check if database exists
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"[INFO] PostgreSQL version: {version.split(',')[0]}")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        if tables:
            print(f"[INFO] Found {len(tables)} existing table(s):")
            for table in tables:
                print(f"  - {table[0]}")
        else:
            print("[INFO] No tables found. Database is ready for initialization.")
        
        cursor.close()
        conn.close()
        print("\n[SUCCESS] Database connection verified! You can now run init_database.py")
        
    except psycopg2.OperationalError as e:
        error_msg = str(e)
        if "password authentication failed" in error_msg:
            print("[ERROR] Password authentication failed!")
            print("Please verify:")
            print("  1. The password in DATABASE_URL matches your PostgreSQL password")
            print("  2. PostgreSQL is running")
            print("  3. The user has permission to access the database")
        elif "could not connect" in error_msg or "connection refused" in error_msg:
            print("[ERROR] Cannot connect to PostgreSQL server!")
            print("Please verify:")
            print("  1. PostgreSQL is running")
            print("  2. PostgreSQL is listening on port", db_port)
            print("  3. The host address is correct")
        elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
            print("[ERROR] Database does not exist!")
            print(f"Please create the database first:")
            print(f"  CREATE DATABASE {db_name};")
        else:
            print(f"[ERROR] Connection error: {e}")
        sys.exit(1)
        
except Exception as e:
    print(f"[ERROR] Failed to parse DATABASE_URL: {e}")
    print("Expected format: postgresql://username:password@host:port/database_name")
    sys.exit(1)

