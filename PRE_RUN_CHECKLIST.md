# ✅ Pre-Run Checklist

**Complete these steps before running the bot:**

---

## 📋 Current Status

### ✅ Ready
- [x] Python 3.13.4 installed
- [x] config.yaml exists
- [x] requirements.txt exists
- [x] Source code ready (all fixes applied)

### ❌ Need Setup
- [ ] .env file with credentials
- [ ] Install Python packages
- [ ] (Optional) Create virtual environment

---

## 🔧 Quick Setup (5 minutes)

### Step 1: Create .env File

```bash
cd /Users/ram_surya/.cursor/worktrees/LinkedIn-Easy-Apply-Bot/vta

# Copy the example
cp .env.example .env

# Edit with your credentials
nano .env
```

**Add your actual LinkedIn credentials:**
```env
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD=your_actual_password
OPENAI_API_KEY=sk-your-key-here  # Optional
```

### Step 2: Install Packages

**Option A: With virtual environment (recommended)**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Option B: Global install (faster for testing)**
```bash
pip3 install -r requirements.txt
```

### Step 3: Verify Installation

```bash
python3 -c "import selenium, undetected_chromedriver; print('✅ Packages installed')"
```

### Step 4: Test Run (Dry Run)

```bash
python3 -m src.main --dry-run
```

---

## 🎯 What to Expect

### During Startup (5-10 seconds)
```
[INFO] Credentials loaded for user: yo***
[INFO] ✅ OpenAI client initialized
[INFO] Q&A Memory: 0 pairs loaded
[INFO] Starting browser...
```

### Browser Opens
- Chrome window appears
- Bot logs into LinkedIn
- Navigates to job search

### Filter Application (First Time)
```
🔧 STEP 1: Applying CONSTANT filters
✅ Experience: Associate, Mid-Senior level
✅ Workplace: Remote, Hybrid, Onsite
✅ Constant filters applied successfully!
```

### Search Loop
```
📅 STEP 2: Starting search loop
🔍 SEARCH 1/5 x 1/3
Position: AI Engineer
Location: San Francisco, CA
📅 [VARIABLE] Applying date filter: 24h
✅ Found 45 jobs to process
```

### During Form Filling

**If question is in memory:**
```
✅ [MEMORY] Found answer for: 'Do you have visa?' -> 'Yes'
```

**If question is new and AI is enabled:**
```
❌ Not in memory: 'Years of experience?'
🤖 Trying AI-powered answer...
✅ [AI] Generated answer: '5'
💾 Saved AI answer to memory
```

**If AI is not available:**
```
❌ Not in memory: 'Years of experience?'
👤 Requesting user input...
👉 Enter answer: _
```

---

## 🐛 Common Issues

### Issue: "No module named 'selenium'"
**Fix**: Run `pip3 install -r requirements.txt`

### Issue: "LINKEDIN_USERNAME must be set"
**Fix**: Create `.env` file with your credentials

### Issue: Chrome driver not found
**Fix**: ChromeDriver is in `assets/` folder - bot will use it automatically

### Issue: Bot opens Chrome but doesn't login
**Fix**: Check your LinkedIn credentials in `.env` file

---

## ✅ Ready to Run?

If you've completed all steps above, run:

```bash
# Test first (recommended)
python3 -m src.main --dry-run

# Real run (submits applications)
python3 -m src.main
```

---

## 📊 Files to Monitor

While bot is running, you can check:

```bash
# Real-time logs
tail -f logs/bot_debug.log

# Q&A memory (grows as bot learns)
cat data/qa_memory.csv

# Applications submitted
cat output/applications.csv
```

---

## 🎉 Success Indicators

You'll know it's working when you see:

1. ✅ Bot logs into LinkedIn successfully
2. ✅ "Constant filters applied successfully!"
3. ✅ "Found X jobs to process"
4. ✅ Forms being filled automatically
5. ✅ Q&A memory growing in `data/qa_memory.csv`

---

**Need help?** See `SETUP_GUIDE.md` for detailed instructions
