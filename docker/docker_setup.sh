#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}NocoDB Web Scraper - Docker Deployment${NC}"
echo -e "${GREEN}========================================${NC}"

# Check if .env file exists
if [ ! -f "../.env" ]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure it.${NC}"
    exit 1
fi

# Check if data directory exists
if [ ! -d "../data" ]; then
    echo -e "${RED}Error: data/ directory not found!${NC}"
    echo -e "${YELLOW}Please ensure the data directory with config files exists.${NC}"
    exit 1
fi

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose down

# Build images
echo -e "${YELLOW}Building Docker images...${NC}"
docker-compose build --no-cache

# Start containers
echo -e "${YELLOW}Starting containers...${NC}"
docker-compose up -d

# Wait for services to be healthy
echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check container status
echo -e "${YELLOW}Container Status:${NC}"
docker-compose ps

# Check logs
echo -e "${YELLOW}Recent logs:${NC}"
docker-compose logs --tail=20

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "Frontend: http://127.0.0.1:8090"
echo -e "Backend API: http://127.0.0.1:8091"
echo -e "Access via nginx: https://your.domain.de"
echo -e ""
echo -e "To view logs: ${YELLOW}docker-compose logs -f${NC}"
echo -e "To stop: ${YELLOW}docker-compose down${NC}"
echo -e "To restart: ${YELLOW}docker-compose restart${NC}"