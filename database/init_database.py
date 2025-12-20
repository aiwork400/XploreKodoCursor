"""
Initialize XploreKodo PostgreSQL database.

Run this script to create all tables in your PostgreSQL 16 database.
Make sure PostgreSQL is running and DATABASE_URL is set correctly.
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent.resolve())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database.db_manager import init_db

if __name__ == "__main__":
    print("Initializing XploreKodo database...")
    print(f"Database URL: {os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/xplorekodo')}")
    
    try:
        init_db()
        print("[SUCCESS] Database tables created successfully!")
        print("\nYou can also run the SQL script directly:")
        print("  psql -U postgres -d xplorekodo -f database/init_db.sql")
    except Exception as e:
        print(f"[ERROR] Error initializing database: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL 16 is running")
        print("2. Database 'xplorekodo' exists (CREATE DATABASE xplorekodo;)")
        print("3. DATABASE_URL environment variable is set correctly in .env file")
        print("4. The password in DATABASE_URL matches your PostgreSQL password")
        sys.exit(1)

