#!/bin/bash

# Algorithm Competition RAG Assistant Startup Script

set -e

echo "🚀 Algorithm Competition RAG Assistant Startup Script"
echo "=================================================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
required_version="3.9"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python version too low, Python 3.9 or higher required"
    exit 1
fi

echo "✅ Python version check passed: $python_version"

# Check dependencies
echo "📦 Checking dependencies..."
if ! python3 -c "import zhipuai, neo4j, numpy" 2>/dev/null; then
    echo "📥 Installing dependency packages..."
    pip3 install -r requirements.txt
fi

echo "✅ Dependencies check completed"

# Check configuration file
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📝 Creating configuration file..."
        cp env.example .env
        echo "⚠️  Please edit the .env file and fill in the correct configuration"
        echo "   Especially ZHIPU_API_KEY and NEO4J_PASSWORD"
    else
        echo "❌ Configuration file template not found"
        exit 1
    fi
fi

# Check Neo4j connection
echo "🔍 Checking Neo4j connection..."
if ! python3 -c "
from src.config.settings import settings
from neo4j import GraphDatabase
try:
    driver = GraphDatabase.driver(settings.database.neo4j_uri, auth=(settings.database.neo4j_user, settings.database.neo4j_password))
    with driver.session() as session:
        session.run('RETURN 1')
    driver.close()
    print('✅ Neo4j connection successful')
except Exception as e:
    print(f'❌ Neo4j connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo "❌ Neo4j connection failed, please check configuration"
    exit 1
fi

# Select startup mode
echo ""
echo "Please select startup mode:"
echo "1. Interactive mode (original functionality)"
echo "2. Web interface"
echo "3. Docker deployment"
echo "4. Exit"
echo ""

read -p "Please enter your choice (1-4): " choice

case $choice in
    1)
        echo "🖥️  Starting interactive mode..."
        python3 cli/main.py
        ;;
    2)
        echo "🌐 Starting web interface..."
        python3 cli/main.py --web
        ;;
    3)
        echo "🐳 Starting Docker deployment..."
        if ! command -v docker-compose &> /dev/null; then
            echo "❌ docker-compose not installed"
            exit 1
        fi
        docker-compose up -d
        echo "✅ Services started"
        echo "📱 Web interface: http://localhost"
        echo "🔧 Neo4j browser: http://localhost:7474"
        ;;
    4)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

