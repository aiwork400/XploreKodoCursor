# XploreKodo Platform - Deployment Guide

This guide explains how to deploy the XploreKodo All-in-One Platform once your hardware is ready.

## 📋 Prerequisites

### Hardware Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 20GB+ free space for database and application
- **Network**: Internet connection for API calls (Google Cloud, OpenAI, Gemini)

### Software Requirements
- **Docker**: Version 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 2.0+ (included with Docker Desktop)
- **Git**: For cloning the repository

### API Keys & Credentials
Before deployment, ensure you have:
1. **Google Cloud Service Account JSON** (`google_creds.json`)
   - Required for: Speech-to-Text, Text-to-Speech, Translation
   - Download from Google Cloud Console
2. **Gemini API Key**
   - Required for: AI Grading, Baseline Assessment, Daily Briefing
   - Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
3. **OpenAI API Key** (Optional, for Phase 2)
   - Required for: Voice-to-Voice features
   - Get from [OpenAI Platform](https://platform.openai.com/api-keys)

## 🚀 Deployment Steps

### Step 1: Clone Repository

```bash
git clone https://github.com/aiwork400/XploreKodoCursor.git
cd XploreKodoCursor
```

### Step 2: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=xplorekodo
POSTGRES_PORT=5432

# Google Cloud Credentials
GOOGLE_APPLICATION_CREDENTIALS=./google_creds.json
GOOGLE_CLOUD_TRANSLATE_PROJECT_ID=your-gcp-project-id
GOOGLE_CLOUD_TRANSLATE_CREDENTIALS_PATH=./google_creds.json

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Optional

# Application Configuration
PHASE_2_ENABLED=True
DEBUG=False
GRADING_STANDARD=XPLOREKODO_STRICT

# Security
SECRET_KEY=generate_a_secure_random_key_here

# Port Configuration
STREAMLIT_PORT=8501
```

**⚠️ Security Note**: Never commit `.env` or `google_creds.json` to version control. They are already in `.gitignore`.

### Step 3: Place Credentials

Place your `google_creds.json` file in the project root directory:

```bash
# Ensure the file is readable
chmod 600 google_creds.json
```

### Step 4: Build and Start Services

```bash
# Build Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### Step 5: Initialize Database

The database will be automatically initialized with migrations on first startup. However, you may want to seed initial data:

```bash
# Enter the app container
docker-compose exec app bash

# Run database initialization (if needed)
python -c "from database.db_manager import init_db; init_db()"

# Seed curriculum data
python scripts/seed_curriculum.py

# Seed Life-in-Japan knowledge base
python scripts/seed_life_in_japan_kb.py

# Exit container
exit
```

### Step 6: Verify Deployment

1. **Check Service Status**:
   ```bash
   docker-compose ps
   ```

2. **Access Dashboard**:
   - Open browser: `http://localhost:8501`
   - You should see the XploreKodo Global Command Center

3. **Check Database Connection**:
   ```bash
   docker-compose exec postgres psql -U postgres -d xplorekodo -c "\dt"
   ```

4. **View Application Logs**:
   ```bash
   docker-compose logs app
   ```

## 🔧 Configuration Options

### Port Configuration

To change the Streamlit port, modify `STREAMLIT_PORT` in `.env` and update `docker-compose.yml`:

```yaml
ports:
  - "8080:8501"  # External:Internal
```

### Database Persistence

Database data is stored in a Docker volume (`postgres_data`). To backup:

```bash
# Backup database
docker-compose exec postgres pg_dump -U postgres xplorekodo > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres xplorekodo < backup.sql
```

### Scaling

For production, consider:
- **Reverse Proxy**: Use Nginx or Traefik in front of Streamlit
- **Database Replication**: Set up PostgreSQL master-slave replication
- **Load Balancer**: Multiple app instances behind a load balancer

## 🛠️ Maintenance

### Update Application

```bash
# Pull latest code
git pull origin master

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f app
docker-compose logs -f postgres
```

### Stop Services

```bash
# Stop (preserves data)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove everything including volumes (⚠️ deletes data)
docker-compose down -v
```

### Database Migrations

New migrations are automatically applied on container startup. To manually run:

```bash
docker-compose exec app python -c "from database.db_manager import init_db; init_db()"
```

## 🔒 Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Set strong `SECRET_KEY` in `.env`
- [ ] Restrict database port exposure (remove from docker-compose.yml ports if not needed externally)
- [ ] Use HTTPS in production (set up reverse proxy with SSL)
- [ ] Regularly update Docker images: `docker-compose pull`
- [ ] Monitor logs for suspicious activity
- [ ] Backup database regularly
- [ ] Keep API keys secure and rotate periodically

## 📊 Monitoring

### Health Checks

Both services include health checks:
- **PostgreSQL**: Checks if database is ready
- **App**: Checks if Streamlit is responding

View health status:
```bash
docker-compose ps
```

### Resource Usage

Monitor resource usage:
```bash
docker stats
```

## 🐛 Troubleshooting

### App Won't Start

1. **Check logs**: `docker-compose logs app`
2. **Verify database connection**: Ensure PostgreSQL is healthy
3. **Check environment variables**: Verify `.env` file is correct
4. **Verify credentials**: Ensure `google_creds.json` exists and is valid

### Database Connection Errors

1. **Check PostgreSQL logs**: `docker-compose logs postgres`
2. **Verify DATABASE_URL** in `.env` matches docker-compose configuration
3. **Test connection**: `docker-compose exec app python -c "from database.db_manager import SessionLocal; db = SessionLocal(); db.execute('SELECT 1'); print('Connected!')"`

### Port Already in Use

If port 8501 is already in use:
1. Change `STREAMLIT_PORT` in `.env`
2. Update port mapping in `docker-compose.yml`
3. Restart: `docker-compose up -d`

### Missing Dependencies

If you see import errors:
1. Rebuild image: `docker-compose build --no-cache`
2. Check `requirements.txt` includes all dependencies

## 📝 Post-Deployment

After successful deployment:

1. **Seed Initial Data**:
   - Run curriculum seeding script
   - Run Life-in-Japan KB seeding script

2. **Create Admin User** (if needed):
   - Access Admin Dashboard
   - Enable Admin Mode in sidebar

3. **Test Core Features**:
   - Create a test candidate
   - Run baseline assessment
   - Test language coaching
   - Verify Support Hub

4. **Set Up Backups**:
   - Schedule regular database backups
   - Store backups securely

## 🌐 Production Considerations

### Recommended Production Setup

1. **Reverse Proxy (Nginx/Traefik)**:
   - SSL/TLS termination
   - Domain name configuration
   - Rate limiting

2. **Database**:
   - Use managed PostgreSQL service (AWS RDS, Google Cloud SQL)
   - Enable automated backups
   - Set up read replicas for scaling

3. **Monitoring**:
   - Set up application monitoring (e.g., Prometheus + Grafana)
   - Log aggregation (e.g., ELK Stack)
   - Error tracking (e.g., Sentry)

4. **Security**:
   - Use secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)
   - Enable firewall rules
   - Regular security audits

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs`
2. Review this guide
3. Check GitHub Issues: https://github.com/aiwork400/XploreKodoCursor/issues

---

**Last Updated**: 2025-12-21
**Platform Version**: 2.0 (Phase 2 + Admin Monitoring + Multi-Stage Journeys)

