# 🚀 LinkedIn Easy Apply Bot - Complete Setup Guide

**Step-by-step instructions to get the bot running in 15 minutes.**

---

## 📋 Quick Checklist

Before you start, make sure you have:

- Python 3.8 or higher installed
- Google Chrome browser installed
- LinkedIn account credentials
- Resume PDF ready
- (Optional) OpenAI API key for AI-powered answers

---

## 🔧 Step-by-Step Setup

### Step 1: Download the Project

```bash
# Option A: Clone from Git
git clone <your-repo-url>
cd LinkedIn-Easy-Apply-Bot

# Option B: Download ZIP and extract
# Then navigate to the extracted folder
```

### Step 2: Verify Python Installation

```bash
# Check Python version (should be 3.8+)
python3 --version
# Example output: Python 3.10.5
```

**If Python is not installed:**

- **macOS**: `brew install python3`
- **Ubuntu/Debian**: `sudo apt install python3 python3-pip`
- **Windows**: Download from [https://www.python.org/downloads/](https://www.python.org/downloads/)

### Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Your terminal should now show (venv) prefix
```

**Troubleshooting:**

- If `python3` command not found, try just `python`
- If `venv` module not found, install with: `pip3 install virtualenv`

### Step 4: Install Dependencies

```bash
# Ensure venv is activated (you should see (venv) in your terminal)
pip install -r requirements.txt

# Wait for installation to complete
# This will install Selenium, undetected-chromedriver, etc.
```

**Expected output:**

```
Successfully installed selenium-4.x.x undetected-chromedriver-3.x.x ...
```

### Step 5: Create Environment File

```bash
# Copy the example file
cp .env.example .env

# Edit the file (use any text editor)
nano .env
# OR
vim .env
# OR open in your favorite editor
```

**Edit `.env` file:**

```env
# REQUIRED: Your LinkedIn credentials
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD=your_actual_password

# OPTIONAL: For AI-powered answers
OPENAI_API_KEY=sk-your-api-key-here
```

**Important Notes:**

- Replace with your ACTUAL LinkedIn email and password
- Do NOT use quotes around values
- Keep this file SECRET - never share or commit to Git
- If you don't have an OpenAI API key, leave it blank or remove the line

### Step 6: Configure Your Job Search

Edit `config.yaml` with your preferences:

```bash
nano config.yaml
# OR open in your favorite editor
```

**Minimum Required Configuration:**

```yaml
# YOUR PHONE NUMBER (required for most applications)
phone_number: 1234567890  # Use your real phone number

# POSITIONS (what roles you're looking for)
positions:
  - AI Engineer
  - Machine Learning Engineer
  - Data Scientist
  # Add more roles here

# LOCATIONS (where you want to work)
locations:
  - San Francisco, CA
  - Remote
  - United States
  # Add more locations here

# SEARCH FILTERS
search:
  filters:
    date_posted: "24h"  # Only jobs from past 24 hours
    workplace_type: ["remote", "hybrid", "onsite"]

# EXPERIENCE LEVEL (set once for all searches)
experience_level:
  - Associate
  - Mid-Senior level

# RESUME UPLOAD (IMPORTANT!)
uploads:
  Resume: /full/path/to/your/resume.pdf
  # Example: /Users/yourname/Documents/MyResume.pdf
  # Windows example: C:/Users/yourname/Documents/MyResume.pdf

# OUTPUT FILE
output_filename:
  - output/applications.csv
```

**Critical Points:**

1. Use YOUR real phone number
2. Choose positions you're ACTUALLY qualified for
3. Set FULL PATH to your resume PDF
4. Adjust experience level to match your profile

### Step 7: Verify ChromeDriver

The project includes ChromeDriver for different operating systems:

```bash
# Check if ChromeDriver exists
ls assets/

# You should see:
# chromedriver_darwin (macOS)
# chromedriver_linux (Linux)
# chromedriver_windows (Windows)
```

**For macOS users:**

```bash
# Give execute permission
chmod +x assets/chromedriver_darwin
```

**For Linux users:**

```bash
chmod +x assets/chromedriver_linux
```

**For Windows users:**

- No special permissions needed
- Windows Defender might flag it - allow it

### Step 8: Test Run (Dry Run)

**ALWAYS do a dry run first!**

```bash
# Make sure venv is activated
python3 -m src.main --dry-run
```

**What to expect:**

1. Chrome browser opens automatically
2. Bot logs into LinkedIn
3. Bot navigates to job search
4. Bot applies constant filters (experience + workplace)
5. Bot searches for jobs
6. Bot clicks job cards and reads forms
7. **Bot DOES NOT submit applications** (dry run mode)

**Watch the terminal for:**

```
[INFO] Credentials loaded for user: yo***
[INFO] ✅ OpenAI client initialized
[INFO] Q&A Memory: 0 pairs loaded
[INFO] 🔧 [CONSTANT] Applying experience level filters...
[INFO] ✅ Constant filters applied successfully!
```

**If you see errors:**

- Check `.env` file has correct credentials
- Verify `config.yaml` has valid paths
- Ensure Chrome browser is installed

### Step 9: Answer First Questions

During dry run, you'll be prompted for unknown questions:

```
================================================================================
[MISSING ANSWER] Q&A Memory Gap Detected!
================================================================================
Question: "How many years of experience do you have with Python?"
================================================================================

👉 Enter answer for this question (or type 'SKIP' to ignore): _
```

**Type your answer:**

```
👉 Enter answer for this question (or type 'SKIP' to ignore): 5
```

**Bot will save it:**

```
✅ Learned: 'How many years...' -> '5'
```

**Answer 10-20 common questions** during dry run to train the bot.

### Step 10: Real Run (Submit Applications)

Once dry run looks good and you've trained the bot:

```bash
# Stop the dry run (Ctrl+C)

# Run for real (this WILL submit applications!)
python3 -m src.main
```

**Monitoring:**

- Keep terminal visible
- Bot will pause if it encounters unknown questions
- Bot will pause if validation errors occur
- Check `output/applications.csv` for submitted applications

---

## 🎯 First Time Best Practices

### During Setup

1. **Use Dry Run First**: Never skip this step!
2. **Start Small**: Test with 1-2 positions first
3. **Train the Bot**: Answer questions during dry run
4. **Verify Filters**: Check that correct filters are applied

### During First Real Run

1. **Stay Near Computer**: Bot might need your input
2. **Monitor Progress**: Watch terminal for errors
3. **Review Applications**: Check `output/applications.csv`
4. **Check Email**: LinkedIn sends confirmation emails

### After First Session

1. **Review Q&A Memory**: Check `data/qa_memory.csv`
2. **Verify Applications**: Check LinkedIn "Jobs" > "Applied Jobs"
3. **Adjust Config**: Fine-tune positions/locations if needed
4. **Plan Next Session**: Bot learns more each time

---

## 📊 Verifying Everything Works

### 1. Check Log File

```bash
# View recent logs
tail -f logs/bot_debug.log
```

**Look for these SUCCESS indicators:**

```
✅ OpenAI client initialized
✅ Constant filters applied successfully!
✅ [MEMORY] Found answer for: '...'
✅ Application submitted successfully
```

### 2. Check Q&A Memory

```bash
# View learned Q&A pairs
cat data/qa_memory.csv
```

**Should look like:**

```csv
question_text,answer_text
"How many years of experience do you have with Python?","5"
"Are you authorized to work in the US?","Yes"
"Do you require visa sponsorship?","No"
```

### 3. Check Applications Log

```bash
# View submitted applications
cat output/applications.csv
```

**Should show:**

```csv
job_id,job_title,company,status,timestamp
3791234567,"AI Engineer","TechCorp","applied","2026-01-23 10:15:30"
```

---

## 🐛 Common Setup Issues

### Issue: "ModuleNotFoundError: No module named 'selenium'"

**Cause**: Dependencies not installed

**Fix**:

```bash
# Ensure venv is activated
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "LINKEDIN_USERNAME and LINKEDIN_PASSWORD must be set"

**Cause**: `.env` file missing or incorrect

**Fix**:

1. Verify `.env` file exists in project root
2. Check it has correct format (no quotes, no spaces around `=`)
3. Verify credentials are correct

### Issue: "chromedriver executable needs to be in PATH"

**Cause**: ChromeDriver permissions or path issue

**Fix**:

```bash
# macOS/Linux
chmod +x assets/chromedriver_darwin  # or chromedriver_linux

# Verify it's there
ls -la assets/chromedriver*
```

### Issue: Bot logs in but doesn't apply filters

**Cause**: LinkedIn page structure changed OR filters not configured

**Fix**:

1. Check `config.yaml` has `experience_level` and `workplace_type`
2. Run in dry-run mode and watch terminal
3. Look for "Applying CONSTANT filters" message
4. Check for errors about filter buttons not found

### Issue: "OpenAI library not installed"

**Cause**: OpenAI package not in requirements.txt or failed to install

**Fix**:

```bash
pip install openai
```

### Issue: Bot asks same questions repeatedly

**Cause**: Q&A memory not saving correctly

**Fix**:

1. Check `data/` folder exists
2. Check `qa_memory.csv` exists in `data/` folder
3. Verify write permissions: `ls -la data/`
4. Try manually creating: `mkdir -p data && touch data/qa_memory.csv`

---

## 🎓 Understanding the Bot's Behavior

### Startup Sequence

1. **Load Configuration**: Reads `config.yaml` and `.env`
2. **Initialize Q&A Memory**: Loads previous answers
3. **Start Browser**: Opens Chrome in stealth mode
4. **Login to LinkedIn**: Uses your credentials
5. **Navigate to Jobs**: Goes to job search
6. **Apply Constant Filters**: Sets experience level + workplace (ONCE)
7. **Start Search Loop**: For each (position, location) combination

### During Each Search

1. **Navigate**: Go to new position + location
2. **Apply Date Filter**: Only variable filter
3. **Load Jobs**: Get list of jobs
4. **For Each Job**:
  - Click job card
  - Check for "Easy Apply" button
  - Click "Easy Apply"
  - Fill form (using memory, AI, or user input)
  - Check for validation errors
  - Submit if no errors

### When Bot Pauses

**Three reasons the bot pauses:**

1. **Unknown Question**: Needs your answer to learn
2. **Validation Error**: Needs you to fix error in browser
3. **Manual Confirmation**: If `require_submission_confirmation: true`

**What to do:**

- Read the terminal message carefully
- Take action in browser if needed
- Press ENTER to continue

---

## 🔐 Security Checklist

Before running:

- `.env` file is in `.gitignore`
- Never shared `.env` file with anyone
- Using strong LinkedIn password
- OpenAI API key (if used) is from official account
- Resume PDF doesn't contain sensitive personal data

---

## 🎉 You're Ready!

If you've followed all steps:

✅ Python environment is set up  
✅ Dependencies are installed  
✅ Configuration files are ready  
✅ You've done a successful dry run  
✅ Bot has learned some Q&A pairs  

**You can now run the bot for real applications!**

```bash
python3 -m src.main
```

**Happy job hunting! 🚀**

---

## 💬 Getting Help

If you're still stuck:

1. **Check Logs**: `tail -f logs/bot_debug.log`
2. **Check Crash Dumps**: `ls crash_dumps/` if bot crashed
3. **Review README.md**: Detailed troubleshooting section
4. **Check Issues**: GitHub issues for similar problems
5. **Create Issue**: Describe your problem with logs

---

## 📚 Next Steps

Once the bot is running smoothly:

1. **Optimize Settings**: Adjust date_posted, positions, locations
2. **Build Q&A Memory**: The more you train it, the better it gets
3. **Enable AI Answers**: Set `OPENAI_API_KEY` for full automation
4. **Monitor Results**: Check which companies respond
5. **Iterate**: Refine your strategy based on results

**Remember**: Quality > Quantity. Apply to jobs you're genuinely qualified for!