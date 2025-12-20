# XploreKodo Database Setup

## PostgreSQL 16 Database Migration

This directory contains the database schema and management tools for XploreKodo.

## Setup Instructions

### 1. Install PostgreSQL 16

Ensure PostgreSQL 16 is installed and running on your system.

### 2. Create Database

```sql
CREATE DATABASE xplorekodo;
```

### 3. Set Environment Variable (Optional)

```bash
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/xplorekodo"
```

Or update `database/db_manager.py` with your connection string.

### 4. Initialize Database

**Option A: Using Python script**
```bash
python database/init_database.py
```

**Option B: Using SQL script directly**
```bash
psql -U postgres -d xplorekodo -f database/init_db.sql
```

## Database Schema

### Tables

1. **candidates** - Core candidate profiles
   - candidate_id (PK)
   - full_name, track
   - Document paths (passport_path, coe_path, transcripts_paths)
   - Student requirements (has_150_hour_study_certificate, has_financial_sponsor_docs)
   - Jobseeker requirements (has_jlpt_n4_or_n5, has_kaigo_skills_test)
   - Status fields (status, travel_ready)

2. **document_vault** - Secure file path references
   - id (PK)
   - candidate_id (FK)
   - doc_type, file_path
   - uploaded_at

3. **curriculum_progress** - Learning progress tracking
   - id (PK)
   - candidate_id (FK, unique)
   - JLPT progress (N5, N4, N3)
   - Kaigo vocational progress
   - AI/ML professional progress
   - Phase 2 AR-VR hooks (dormant)

4. **payments** - Payment transactions
   - id (PK)
   - candidate_id (FK)
   - amount, currency, provider
   - transaction_id, status
   - created_at

## Usage

The DatabaseAgent now uses these real database tables instead of in-memory lists.

Example:
```python
from database.db_manager import SessionLocal, Candidate

db = SessionLocal()
candidates = db.query(Candidate).all()
db.close()
```

## Notes

- All timestamps use UTC
- Foreign keys have CASCADE delete
- Indexes are created for performance
- Triggers update `updated_at` automatically

