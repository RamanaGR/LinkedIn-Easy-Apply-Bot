#!/bin/bash
# Quick start script for LinkedIn Easy Apply Bot

set -e  # Exit on error

echo "============================================"
echo "LinkedIn Easy Apply Bot v2.0"
echo "============================================"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run: python3 -m venv venv"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please create .env file from .env.example"
    echo "Run: cp .env.example .env"
    exit 1
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
if ! python -c "import undetected_chromedriver" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Environment ready!"
echo ""

# Parse command line arguments
DRY_RUN=""
HEADLESS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            echo "🔵 DRY RUN MODE: Applications will be simulated"
            shift
            ;;
        --headless)
            HEADLESS="--headless"
            echo "👻 HEADLESS MODE: Browser will not be visible"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo ""
echo "🚀 Starting bot..."
echo ""

# Run the bot
python -m src.main $DRY_RUN $HEADLESS

echo ""
echo "============================================"
echo "Bot session completed!"
echo "Check logs/ directory for details"
echo "============================================"
