#!/bin/bash

# LinkedIn Easy Apply Bot - Dependency Installation Script
# This script installs all required Python packages with SSL workarounds

set -e  # Exit on error

echo "================================================"
echo "LinkedIn Easy Apply Bot - Installing Dependencies"
echo "================================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

echo ""
echo "Installing required packages..."
echo ""

# Install with SSL certificate workarounds
pip3 install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt

echo ""
echo "================================================"
echo "Verifying installation..."
echo "================================================"

# Test imports
python3 << 'EOF'
import sys

packages = [
    ('selenium', 'Selenium WebDriver'),
    ('undetected_chromedriver', 'Undetected ChromeDriver'),
    ('yaml', 'PyYAML'),
    ('dotenv', 'Python Dotenv'),
    ('pypdf', 'PyPDF'),
    ('openai', 'OpenAI')
]

all_success = True
for package, name in packages:
    try:
        __import__(package)
        print(f'✅ {name} installed successfully')
    except ImportError:
        print(f'❌ {name} NOT installed')
        all_success = False

if all_success:
    print('\n✅ All dependencies installed successfully!')
else:
    print('\n⚠️  Some dependencies failed to install')
    sys.exit(1)
EOF

echo ""
echo "================================================"
echo "Installation complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Create .env file with your credentials:"
echo "   cp .env.example .env"
echo "   # Edit .env with your LinkedIn username/password"
echo ""
echo "2. Test the bot:"
echo "   python3 -m src.main --dry-run"
echo ""
echo "3. Run the bot:"
echo "   python3 -m src.main"
echo ""
