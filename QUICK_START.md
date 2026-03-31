# ⚡ Quick Start - Get Running in 5 Minutes

**For experienced users who want to start FAST.**

---

## 🏃 Speed Run

```bash
# 1. Setup
cd LinkedIn-Easy-Apply-Bot/vta
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
nano .env  # Add your LinkedIn credentials

# 3. Test
python3 -m src.main --dry-run

# 4. Run (when ready)
python3 -m src.main
```

---

## 📝 Minimum Required Config

**`.env` file:**
```env
LINKEDIN_USERNAME=your.email@example.com
LINKEDIN_PASSWORD=your_password

# LLM provider (recommended: ollama)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://127.0.0.1:11434
# Optional: pin a model name (leave empty for auto-select)
OLLAMA_MODEL=

# Optional (only needed when AI_PROVIDER=openai)
OPENAI_API_KEY=sk-optional-api-key
```

**`config.yaml` (key settings):**
```yaml
phone_number: 1234567890

positions:
  - AI Engineer
  - Data Scientist

locations:
  - Remote
  - United States

search:
  filters:
    date_posted: "24h"
    workplace_type: ["remote", "hybrid"]

experience_level:
  - Associate
  - Mid-Senior level

uploads:
  Resume: /full/path/to/resume.pdf

output_filename:
  - output/applications.csv
```

---

## ✅ Quick Verification

After dry run, check:

```bash
# Check logs
tail -20 logs/bot_debug.log

# Should see:
# ✅ AI Question Answering: ACTIVE
# ✅ Ollama model ready: <model>
# ✅ Constant filters applied
# ✅ Found X jobs to process
```

---

## 🎯 What Happens

1. **Startup** (once):
   - Bot logs into LinkedIn
   - Applies constant filters (experience + workplace)

2. **For each search** (position + location):
   - Applies date filter
   - Processes all Easy Apply jobs
   - Uses memory/AI to fill forms
   - Submits if no errors

3. **Learning**:
   - Unknown questions → AI tries first → asks you if AI fails
   - Your answers saved to `qa_memory.csv`
   - Next time → auto-filled

---

## 🚨 Common First-Time Issues

**Bot asks for password**: Just enter it, it's not saving anywhere

**Unknown questions**: Answer them - bot learns for next time

**Validation errors**: Fix in browser, press ENTER, bot learns the fix

**Filters not applying**: Check logs for "Constant filters applied" message

---

## 📊 After First Run

Check results:
```bash
# Applications submitted
cat output/applications.csv

# Q&A learned
cat data/qa_memory.csv

# Full logs
cat logs/bot_debug.log
```

---

## 🎓 Next Steps

1. **Review applications** - Check what was submitted
2. **Build memory** - Answer more questions to train bot
3. **Optimize config** - Refine positions/locations
4. **Enable AI** - Set OpenAI API key for full automation
4. **Enable AI** - Run Ollama locally and set `AI_PROVIDER=ollama` (or set `AI_PROVIDER=openai` + `OPENAI_API_KEY`)

---

**For detailed setup:** See `SETUP_GUIDE.md`  
**For troubleshooting:** See `README.md` (Troubleshooting section)

**Happy hunting! 🚀**
