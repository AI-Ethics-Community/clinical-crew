#!/bin/bash

# Clinical Crew - Quick Start Script
# This script helps you get started quickly with the application

set -e  # Exit on error

echo "=================================================="
echo "  Clinical Crew - Quick Start"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}✗ Please edit .env file and add your GEMINI_API_KEY${NC}"
    echo -e "${YELLOW}  Then run this script again.${NC}"
    exit 1
fi

# Check if GEMINI_API_KEY is set
if ! grep -q "GEMINI_API_KEY=your_gemini_api_key_here" .env && grep -q "GEMINI_API_KEY=" .env; then
    echo -e "${GREEN}✓ .env file configured${NC}"
else
    echo -e "${RED}✗ Please set your GEMINI_API_KEY in the .env file${NC}"
    exit 1
fi

# Check Python version
echo ""
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo -e "${GREEN}✓ Python $python_version${NC}"
else
    echo -e "${RED}✗ Python 3.11+ required (found $python_version)${NC}"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Check if Docker is running
echo ""
echo "Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Docker is not running. Please start Docker.${NC}"
    echo -e "${YELLOW}  MongoDB will not be available.${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo -e "${GREEN}✓ Docker is running${NC}"

    # Start MongoDB
    echo ""
    echo "Starting MongoDB with Docker Compose..."
    docker-compose up -d mongodb
    echo -e "${GREEN}✓ MongoDB started${NC}"

    # Wait for MongoDB to be ready
    echo ""
    echo "Waiting for MongoDB to be ready..."
    sleep 5
    echo -e "${GREEN}✓ MongoDB is ready${NC}"
fi

# Create directories
echo ""
echo "Creating directories..."
mkdir -p data/vectorstore
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"

# Summary
echo ""
echo "=================================================="
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo "=================================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start the API server:"
echo "   python -m app.main"
echo ""
echo "2. Access the API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "3. Try the example script:"
echo "   python example_usage.py"
echo ""
echo "4. (Optional) Index your knowledge base:"
echo "   python -m app.rag.document_indexer --all"
echo ""
echo "=================================================="
echo ""
