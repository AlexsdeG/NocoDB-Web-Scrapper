# Docker Deployment Guide

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- System Nginx configured with SSL (optional)
- NocoDB instance accessible

## Project Structure

```
NocoDB-Web-Scrapper/
├── docker/                    # Docker configuration (you are here)
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   ├── docker-compose.yml
│   ├── docker_setup.sh
│   └── README.md
├── backend/                   # Backend Python FastAPI
│   ├── .env                   # Environment variables (create from .env.example)
│   ├── .env.example
│   ├── data/                  # Configuration files
│   │   ├── config.json
│   │   ├── login.json
│   │   ├── user_map.json
│   │   ├── scrapers.json
│   │   └── ux.json
│   └── *.py
├── frontend/                  # Frontend HTML/CSS/JS
│   ├── index.html
│   ├── css/
│   └── js/
└── nginx/                     # System nginx config (optional)
    └── nginx.config
```

## Quick Start

### 1. Prepare Environment

```bash
# Ensure you're in the project root
cd /home/alexsdeg/Documents/Programming/NocoDB-Web-Scrapper

# Create .env from example
cp backend/.env.example backend/.env

# Edit with your credentials
nano backend/.env
```

### 2. Deploy with Docker Compose

```bash
# Navigate to docker directory
cd docker

# Make deploy script executable
chmod +x docker_setup.sh

# Run deployment
./docker_setup.sh
```

### 3. Manual Deployment

```bash
# Navigate to docker directory
cd docker

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
cd docker
docker-compose start
```

### Stop Services
```bash
cd docker
docker-compose stop
```

### Restart Services
```bash
cd docker
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
cd ..
git pull

# Rebuild and restart
cd docker
docker-compose up -d --build
```

### Remove Everything
```bash
cd docker
docker-compose down -v
```

## Ports

- **8091**: Backend API (accessible at 127.0.0.1:8091)
- **8090**: Frontend Nginx (accessible at 127.0.0.1:8090)

### With System Nginx

If you have system nginx configured, it will proxy:
- HTTPS (443) → Frontend (127.0.0.1:8090)
- HTTPS (443)/api/ → Backend (127.0.0.1:8091)

### Without System Nginx

Access directly:
- Frontend: http://127.0.0.1:8090
- Backend API: http://127.0.0.1:8091

## Data Persistence

The following are mounted as volumes:
- `backend/data/` - Configuration and user data (JSON files)
- `backend-logs` - Application logs (Docker named volume)

## System Nginx Setup (Optional)

If you want to use system nginx with SSL:

```bash
# Copy the config to nginx sites-available
sudo cp ../nginx/nginx.config /etc/nginx/sites-available/nocodb-scraper

# Edit to add your domain and SSL certificate paths
sudo nano /etc/nginx/sites-available/nocodb-scraper

# Enable the site
sudo ln -s /etc/nginx/sites-available/nocodb-scraper /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

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

### Test Backend Directly
```bash
# From your host machine
curl http://127.0.0.1:8091/status

# Should return API and NocoDB status
```

### Test Frontend Directly
```bash
# From your host machine
curl http://127.0.0.1:8090/

# Should return HTML content
```

### Common Issues

**Issue**: Container exits immediately
```bash
# Check logs for errors
docker-compose logs backend

# Common causes:
# - Missing .env file
# - Invalid NocoDB credentials
# - Missing data files
```

**Issue**: Can't connect to NocoDB
```bash
# Verify NocoDB URL is accessible from container
docker exec -it nocodb-scraper-backend curl https://your-nocodb-url.com

# Check .env file has correct NOCODB_URL
```

**Issue**: Playwright/Chromium errors
```bash
# Rebuild backend without cache
docker-compose build --no-cache backend
docker-compose up -d backend
```

### Reset Everything
```bash
cd docker
docker-compose down -v
docker system prune -a
docker-compose up -d --build
```

## Production Checklist

- [ ] `backend/.env` file configured with secure credentials
- [ ] All files in `backend/data/` directory exist and are valid JSON
- [ ] System Nginx SSL certificates installed (if using system nginx)
- [ ] NocoDB instance accessible and API token valid
- [ ] Firewall configured (only expose 80/443 to public if using system nginx)
- [ ] Docker containers set to `restart: unless-stopped`
- [ ] Backup strategy for `backend/data/` directory
- [ ] Log rotation configured for Docker logs
- [ ] Monitor disk space for Docker volumes

## Development vs Production

### Development
```bash
# Run with live logs
docker-compose up --build

# Enable more verbose logging
# Edit backend/.env: DEBUG=true
```

### Production
```bash
# Run in detached mode
docker-compose up -d --build

# Ensure restart policy is set
# Already configured in docker-compose.yml
```