# 🚀 LinkedIn Easy Apply Bot

**Intelligent, self-learning job application automation for LinkedIn with AI-powered answers and smart filtering.**

---

## ✨ Features

### 🎯 Smart Search Strategy
- **Constant Filters**: Experience level and workplace type set ONCE for all searches
- **Variable Filters**: Date posted changes per search (role + location combination)
- **Methodical Approach**: Systematically searches all position × location combinations

### 🤖 Intelligent Form Filling
- **Self-Learning Q&A System**: Remembers your answers in `qa_memory.csv`
- **AI-Powered Answers**: Local (Ollama) or optional OpenAI integration for automatic question answering
- **Priority System**:
  1. Check memory for known answers
  2. Try AI-powered answer (if an LLM provider is enabled)
  3. Ask user and learn for future applications

### 🛡️ Error-Aware Processing
- **Validation Detection**: Detects red error messages before submission
- **Blocking Behavior**: Never submits applications with validation errors
- **Learning from Fixes**: Saves your manual corrections for future use

### 📊 Additional Features
- **Crash Dumps**: Saves HTML snapshots when errors occur
- **Stealth Mode**: Uses undetected ChromeDriver with human-like behavior
- **Progress Tracking**: Detailed logging and statistics
- **Dry Run Mode**: Test without submitting applications

---

## 🛠️ Installation & Setup

### Prerequisites

- **Python 3.8+**
- **Google Chrome** browser
- **LinkedIn** account
- **LLM provider** (optional): Ollama (local) or OpenAI (cloud)

### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd LinkedIn-Easy-Apply-Bot
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
# OR
venv\Scripts\activate     # Windows
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root:

```env
# Required: LinkedIn Credentials
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD=your_password

# LLM provider (recommended: ollama)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
# Optional: pin a model name (leave empty for auto-select)
OLLAMA_MODEL=

# Optional (only when AI_PROVIDER=openai):
OPENAI_API_KEY=sk-your-api-key-here
```

**Important**: Keep your `.env` file secret! Never commit it to version control.

### Step 5: Configure Job Search

Edit `config.yaml`:

```yaml
phone_number: 1234567890  # Your phone number

# Positions to search for
positions:
  - AI Engineer
  - Machine Learning Engineer
  - Data Scientist

# Locations to search in
locations:
  - San Francisco, CA
  - Remote
  - United States

# Search Filters
search:
  filters:
    date_posted: "24h"  # Options: "24h", "week", "month", "any"
    workplace_type: ["remote", "hybrid", "onsite"]  # Multiple selections OK

# CONSTANT FILTERS (set once for all searches)
experience_level:
  - Associate
  - Mid-Senior level
  # Options: "Entry level", "Associate", "Mid-Senior level", "Director", "Executive", "Internship"

# Submission Settings
require_submission_confirmation: false  # Set true for manual review before submit

# File Uploads
uploads:
  Resume: /path/to/your/resume.pdf
  Cover Letter: /path/to/your/cover_letter.pdf

# Output
output_filename:
  - output/applications.csv

# Optional: Companies to skip
# blacklist:
#   - Company Name 1
#   - Company Name 2
```

---

## 🏃 Usage

### Normal Mode (Submit Applications)

```bash
python3 -m src.main
```

### Dry Run Mode (Test Without Submitting)

```bash
python3 -m src.main --dry-run
```

---

## 🎓 How It Works

### 1. Filter Strategy (OPTIMIZED)

**At Start:**
1. Bot navigates to first search
2. Applies **CONSTANT filters ONCE**:
   - Experience Level (e.g., Associate, Mid-Senior)
   - Workplace Type (e.g., Remote, Hybrid, Onsite)
3. These filters **remain active** for all searches

**For Each Search:**
1. Navigate to new (position + location)
2. Apply **ONLY date posted filter** (e.g., Past 24 hours)
3. Process all jobs in filtered results

**Why This Works:**
- LinkedIn keeps experience level and workplace filters active across searches
- Only role, location, and date posted change per search
- Much faster than re-applying all filters every time

### 2. Self-Learning Q&A System

**First Time You See a Question:**

```
================================================================================
[MISSING ANSWER] Q&A Memory Gap Detected!
================================================================================
Question: "How many years of experience do you have with Python?"
================================================================================

👉 Enter answer for this question (or type 'SKIP' to ignore): 5
```

**Bot Saves Your Answer:**
```
✅ Learned: 'How many years of experience...' -> '5'
💾 Saved to qa_memory.csv
```

**Next Time:**
```
✅ [MEMORY] Found answer for: 'How many years of experience...' -> '5'
(Automatically fills the field)
```

### 3. AI-Powered Answer Flow

If a question is **not** in memory:

1. **Try AI First** (if `OPENAI_API_KEY` is set):
1. **Try AI First** (if an LLM provider is enabled):
   ```
   🤖 Trying AI-powered answer...
   ✅ [AI] Generated answer: 'Yes'
   💾 Saved AI answer to memory
   ```

2. **Ask User** (if AI didn't provide answer):
   ```
   👤 Requesting user input...
   👉 Enter answer: ...
   ```

3. **Remember for Future**: All answers (AI or user) are saved to `qa_memory.csv`

### 4. Validation Error Handling

**Before Submission:**

If bot detects red error text:
```
⚠️  VALIDATION ERRORS DETECTED - EXECUTION PAUSED
================================================================================
1. Field: 'Mobile phone number'
   Error: Please enter a valid answer
================================================================================

👉 Please fix the error in the browser window,
   then press ENTER here to continue...
```

**After You Fix:**
```
✅ Saved to qa_memory.csv: 'Mobile phone number' -> '7542757752'
✅ All validation errors resolved!
Continuing with application...
```

**Bot Never Submits with Errors** - It will always pause and wait for you to fix issues.

---

## 📁 Project Structure

```
LinkedIn-Easy-Apply-Bot/
├── .env                    # Credentials (create this, not in repo)
├── .env.example            # Template for .env
├── config.yaml             # Job search configuration
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── QUICK_START.md         # Short setup & run guide
├── SETUP_GUIDE.md         # Detailed setup
├── _trash/                # Archived docs & dev scripts (optional; see _trash/README.md)
│
├── src/
│   ├── main.py            # Main entry point
│   ├── bot.py             # Browser automation
│   ├── job_search.py      # Search & filtering
│   ├── application.py     # Form filling & submission
│   ├── qa_manager.py      # Self-learning Q&A system
│   ├── config.py          # Configuration loader
│   ├── logger.py          # Logging setup
│   └── utils.py           # Utility functions
│
├── output/
│   └── applications.csv   # Application history
│
├── data/
│   └── qa_memory.csv      # Learned Q&A pairs
│
└── crash_dumps/           # HTML dumps on errors
    └── crash_dump_*.html
```

---

## 🔧 Troubleshooting

### Bot is Not Applying Filters

**Symptoms**: Jobs from all experience levels or workplace types appear

**Fix**:
1. Check `config.yaml` - ensure filters are configured
2. Run in dry-run mode to see filter application logs
3. Check logs for "Applying CONSTANT filters" message
4. Verify "Show results" button is being clicked (check logs)

### Q&A Learning Not Working

**Symptoms**: Bot asks same questions repeatedly

**Fix**:
1. Check if `qa_memory.csv` exists in `data/` folder
2. Check file permissions (bot needs write access)
3. Look for "✅ Learned" messages in logs
4. Manually verify CSV file has new entries after answering

### AI Answers Not Working

**Symptoms**: Bot always asks user, never uses AI

**Fix**:
1. Verify `OPENAI_API_KEY` is set in `.env` file
2. Check logs for "✅ OpenAI client initialized" message
3. If you see "OpenAI library not installed", run: `pip install openai`
4. Verify API key is valid (not expired)

### Bot Gets Stuck on a Form

**Symptoms**: Bot doesn't progress past a certain step

**Fix**:
1. Check logs for validation errors
2. Look in `crash_dumps/` for HTML snapshot
3. Manually fill problematic field in browser
4. Press ENTER when bot prompts
5. Bot will learn from your fix

### ChromeDriver Errors

**Symptoms**: "chromedriver executable needs to be in PATH"

**Fix**:
1. Check if ChromeDriver binary exists in `assets/` folder
2. Verify it has execute permissions: `chmod +x assets/chromedriver_darwin`
3. If missing, download from: https://chromedriver.chromium.org/
4. Place in `assets/` folder with correct name for your OS

---

## 📊 Understanding the Logs

### Startup Logs
```
[INFO] Credentials loaded for user: jo***
[INFO] ✅ OpenAI client initialized
[INFO] Q&A Memory: 15 pairs loaded
```

### Filter Application
```
🔧 [CONSTANT] Applying experience level filters: ['Associate', 'Mid-Senior level']
✅ Clicked 'Show results' button for Experience Level
🔧 [CONSTANT] Applying workplace filters: ['remote', 'hybrid']
✅ Clicked 'Show results' button for Workplace Type
✅ Constant filters applied successfully!
```

### Search Progress
```
🔍 SEARCH 1/5 x 1/3
Position: AI Engineer
Location: San Francisco, CA
📅 [VARIABLE] Applying date filter: 24h
✅ Found 45 jobs to process
```

### Q&A Learning
```
✅ [MEMORY] Found answer for: 'Do you have a visa?' -> 'Yes'
❌ Not in memory: 'Years of experience with TensorFlow?'
🤖 Trying AI-powered answer...
✅ [AI] Generated answer: '3'
💾 Saved AI answer to memory
```

### Application Status
```
✅ Application submitted successfully
Applications: 12 applied, 3 failed, 5 skipped
```

---

## 🎯 Best Practices

### First-Time Setup

1. **Start with Dry Run**:
   ```bash
   python3 -m src.main --dry-run
   ```
   
2. **Keep Terminal Visible**: Watch for prompts asking for input

3. **Answer 10-20 Questions**: Build up your Q&A memory

4. **Switch to Normal Mode**: Once you've trained the bot

### Ongoing Usage

1. **Monitor First Few Applications**: Ensure filters are working correctly

2. **Check `qa_memory.csv` Periodically**: Verify it's learning and growing

3. **Review `output/applications.csv`**: Track which jobs you've applied to

4. **Use Dry Run for Testing**: When changing configuration

### Optimizing Performance

1. **Enable AI Answers**: Set `AI_PROVIDER=ollama` (and run Ollama) or set `AI_PROVIDER=openai` + `OPENAI_API_KEY`

2. **Refine Positions List**: Focus on specific roles to reduce noise

3. **Adjust Date Filter**: Use "24h" for fresh jobs, "week" for more volume

4. **Set Time Limits**: Configure `max_search_time` in config to control session length

---

## 🔐 Security & Privacy

### What the Bot Does

- ✅ Stores credentials in `.env` (local only)
- ✅ Saves your answers in `qa_memory.csv` (local only)
- ✅ Logs activity to `bot_debug.log` (local only)
- ✅ Never shares data with third parties
- ✅ Uses Ollama or OpenAI depending on `AI_PROVIDER` (optional)

### What You Should Do

- 🔒 Never commit `.env` file to Git
- 🔒 Keep `qa_memory.csv` private (contains your answers)
- 🔒 Review applications in `output/applications.csv` before sharing
- 🔒 Use a strong LinkedIn password
- 🔒 Rotate OpenAI API keys regularly

---

## 🤝 Contributing

Found a bug? Want to add a feature? Contributions are welcome!

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## 📝 License

See `LICENSE` file for details.

---

## 🆘 Support

### Common Questions

**Q: How many applications per hour?**  
A: Depends on form complexity. Typically 10-20 applications per hour after initial training.

**Q: Will this get my LinkedIn account banned?**  
A: The bot uses undetected ChromeDriver and human-like delays to avoid detection. However, use responsibly and don't spam applications.

**Q: Can I run this on a server?**  
A: Yes, but you need a display/X server for Chrome. Consider using Xvfb on Linux.

**Q: Does this work with LinkedIn Premium?**  
A: Yes, works with both free and premium accounts.

**Q: What if a job application has multiple pages?**  
A: The bot handles multi-page applications automatically, learning as it goes.

---

## 🎉 Success Tips

1. **Be Selective**: Focus on positions you're genuinely qualified for
2. **Keep Resume Updated**: Ensure your uploaded resume is current
3. **Monitor Applications**: Check email for interview requests
4. **Personalize When Possible**: Use cover letters for important applications
5. **Use Dry Run First**: Always test with new configurations

---

## 📈 Version History

### v3.0 (Current) - January 2026
- ✅ Fixed filter application (constant filters approach)
- ✅ Fixed self-learning Q&A system
- ✅ Fixed AI-powered answer integration
- ✅ Optimized filter strategy (set once, not per search)
- ✅ Enhanced logging and error reporting
- ✅ Clean project structure and documentation

### v2.1
- Added validation error detection
- Implemented Q&A memory system
- Added OpenAI integration

### v2.0
- Multi-page form support
- Crash dump debugging
- Improved stealth mode

### v1.0
- Initial release
- Basic Easy Apply automation

---

**Happy Job Hunting! 🎯**

*Remember: This bot is a tool to help you apply more efficiently. Always ensure your applications are genuine and you're qualified for the positions.*
