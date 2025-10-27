# Docker Deployment Guide

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- System Nginx configured with SSL
- NocoDB instance accessible

## Quick Start

### 1. Prepare Environment

```bash
# Copy environment template
cp ../.env.example ../.env

# Edit with your credentials
nano ../.env
```

### 2. Deploy with Docker Compose

```bash
# Navigate to docker directory
cd backend/docker

# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### 3. Manual Deployment

```bash
# Build and start containers
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Container Management

### Start Services
```bash
docker-compose start
```

### Stop Services
```bash
docker-compose stop
```

### Restart Services
```bash
docker-compose restart
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Update and Rebuild
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

## Ports

- **8091**: Backend API (accessible at 127.0.0.1:8091)
- **8090**: Frontend Nginx (accessible at 127.0.0.1:8090)

System Nginx proxies:
- HTTPS (443) → Frontend (8090)
- HTTPS (443)/api/ → Backend (8091)

## Data Persistence

The following directories are mounted as volumes:
- `backend/data/` - Configuration and user data
- `backend-logs` - Application logs (Docker volume)

## Troubleshooting

### Check Container Health
```bash
docker-compose ps
docker inspect nocodb-scraper-backend --format='{{.State.Health.Status}}'
```

### Access Container Shell
```bash
# Backend
docker exec -it nocodb-scraper-backend /bin/bash

# Frontend
docker exec -it nocodb-scraper-frontend /bin/sh
```

### View Real-time Logs
```bash
docker-compose logs -f --tail=100
```

### Reset Everything
```bash
docker-compose down -v
docker-compose up -d --build
```

## Production Checklist

- [ ] `.env` file configured with secure credentials
- [ ] System Nginx SSL certificates installed
- [ ] NocoDB instance accessible and API token valid
- [ ] Firewall configured (only expose 80/443 to public)
- [ ] Docker containers set to restart unless-stopped
- [ ] Log rotation configured
- [ ] Backup strategy for `data/` directory