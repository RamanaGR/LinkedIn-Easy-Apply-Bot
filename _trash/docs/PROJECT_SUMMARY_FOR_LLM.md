# LinkedIn Easy Apply Bot — Detailed Project Summary for LLM Teaching

This document is a structured summary of the LinkedIn Easy Apply Bot codebase, intended for teaching other LLMs how the project works, how components interact, and where to make changes.

---

## 1. Project Overview

### Purpose
Automate applying to LinkedIn jobs that use **Easy Apply**: search by position and location, open each job, click Easy Apply, fill forms (with optional AI answers), and submit—while learning from user corrections and avoiding detection.

### High-Level Behavior
1. **Login** to LinkedIn via browser automation (undetected Chrome).
2. **Search** jobs by iterating over `positions × locations` with URL-embedded filters (date posted, workplace type, experience level).
3. **For each job card**: open details → check Easy Apply → fill form (phone, uploads, Q&A from memory or AI) → handle validation errors (pause for user fix and learn) → submit or discard.
4. **Learning**: unknown questions and validation fixes are stored in `qa_memory.csv` for future runs.

### Tech Stack
- **Python 3.8+**
- **Browser**: `undetected-chromedriver` + Selenium (Chrome)
- **Config**: YAML (`config.yaml`) + `.env` (credentials, optional OpenAI key)
- **AI**: Optional OpenAI API (GPT-3.5-turbo) for answering form questions with resume context
- **Data**: CSV for Q&A memory (`qa_memory.csv`) and application log (`output/applications.csv`)

---

## 2. Architecture and Data Flow

### Component Diagram (Conceptual)

```
main.py (LinkedInEasyApplyBot)
    │
    ├── Config (config.py)          ← config.yaml + .env
    ├── LinkedInBot (bot.py)        ← browser, login, navigate
    ├── JobSearch (job_search.py)   ← build URL, get cards, click card, Easy Apply check
    └── JobApplication (application.py)
            ├── AIQuestionAnswerer  ← OpenAI + resume PDF context
            ├── QAMemoryManager     ← qa_memory.csv load/save/lookup/learn
            └── Form filling + validation + submit/discard
```

### Execution Flow (Simplified)

1. **Startup**: Load `Config` → init `LinkedInBot` → login → init `JobSearch` and `JobApplication` → navigate to jobs.
2. **Loop** (bounded by `max_search_time`):
   - For each `(position, location)`:
     - `JobSearch.search_jobs(position, location)` → builds URL with all filters, `driver.get(url)`.
     - `JobSearch.get_job_cards()` → scroll list, collect `data-job-id` elements, skip blacklist/applied.
     - For each job: `click_job_card` → `has_easy_apply_button` → `JobApplication.apply_to_job(...)`.
3. **apply_to_job**:
   - `_click_easy_apply()` → click button, then `_check_rate_limit()` (raises `DailyLimitReachedException` if LinkedIn daily limit detected).
   - `_fill_application_form()` in a loop (max iterations):
     - Fill phone, upload docs, `_answer_questions()` (memory → AI → leave blank).
     - `_handle_validation_errors_with_learning()`: if red errors → pause, user fixes, bulk-scrape form into Q&A memory.
     - `_get_next_action()` → "next" | "review" | "submit".
     - If "submit": final validation check → `_submit_application()` (or dry-run discard).
   - Log to `output/applications.csv`.
4. **Shutdown**: Print stats, close browser.

### Key Files and Roles

| File | Role |
|------|------|
| `src/main.py` | Entry point, CLI (`--config`, `--dry-run`, `--headless`), orchestrator loop, stats |
| `src/config.py` | Load YAML + dotenv, expose properties (positions, locations, filters, uploads, blacklist, etc.) |
| `src/bot.py` | Chrome setup (stealth options), login, navigate to jobs, close |
| `src/job_search.py` | Build search URL with filters, get job cards, click card, get title/company, Easy Apply button check |
| `src/application.py` | Easy Apply click, rate-limit check, form fill (phone, uploads, Q&A), validation handling, next/review/submit, crash dumps, CSV log |
| `src/qa_manager.py` | Load/save `qa_memory.csv`, lookup (exact + fuzzy), learn_answer, deduplicate |
| `src/utils.py` | Stealth: human_sleep, type_like_human, smooth_scroll_to_element, random_scroll |
| `src/logger.py` | Central logger for the app |

---

## 3. Module-by-Module Summary

### 3.1 `main.py` — Orchestrator

- **Class**: `LinkedInEasyApplyBot`.
- **Constructor**: Takes `config_file`, `dry_run`, `headless`; loads `Config`, does not start browser yet.
- **run()**: Creates `LinkedInBot` → login; creates `JobSearch` and `JobApplication`; navigates to jobs; runs `_application_loop()`; prints stats; handles `DailyLimitReachedException`, `KeyboardInterrupt`, and generic `Exception`.
- ** _application_loop()**: Iterates over `positions × locations`, enforces `max_search_time`, calls `_search_and_apply_with_filters(position, location)` and human sleep between searches.
- **_search_and_apply_with_filters()**: Calls `job_search.search_jobs(position, location)`, then `job_search.get_job_cards()`, then `_process_job_list(jobs)`.
- **_process_job_list()**: For each job: click card, check Easy Apply, get title/company, check blacklist_titles, call `application.apply_to_job(...)`, update stats; on `DailyLimitReachedException` re-raises to stop run.

### 3.2 `config.py` — Configuration

- **Config**: Loads `config.yaml` into `_config`, loads `.env` via `python-dotenv`.
- **Credentials** (required): `LINKEDIN_USERNAME`, `LINKEDIN_PASSWORD` from env; (optional) `OPENAI_API_KEY`.
- **Properties** (from YAML): `phone_number`, `salary`, `rate`, `positions`, `locations`, `uploads`, `output_filename`, `blacklist`, `blacklist_titles`, `experience_level`, `max_search_time`, `require_submission_confirmation`, `date_posted_filter`, `workplace_type_filters`.
- **output_filename**: If list in YAML, first element is used (e.g. `output/applications.csv`).

### 3.3 `bot.py` — Browser and Login

- **LinkedInBot**: Holds `driver` (undetected Chrome), `wait` (WebDriverWait 30s).
- **_setup_browser()**: ChromeOptions (maximized, disable automation flags, random user-agent, prefs), optional headless; on macOS sets `binary_location` to system Chrome; `uc.Chrome(version_main=144, use_subprocess=True)`; CDP script to hide `navigator.webdriver`.
- **login()**: Go to LinkedIn login page; fill username/password with `StealthUtils.type_like_human`; click submit; wait; success if URL contains "feed" or "mynetwork"; if "checkpoint"/"challenge", wait 60s for user.
- **navigate_to_jobs()**: `driver.get("https://www.linkedin.com/jobs/")`.
- **close()**: `driver.quit()`.

### 3.4 `job_search.py` — Search and Job List

- **JobSearch**: Needs `driver` and `Config`; keeps `applied_job_ids` set.
- **build_search_url(position, location, page=0)**: Base `https://www.linkedin.com/jobs/search/?` with params: `f_AL=true` (Easy Apply), `keywords`, `location`, `start=page*25`, and optionally `f_TPR` (date: 24h/week/month), `f_WT` (workplace: remote/hybrid/onsite), `f_E` (experience level). Returns full URL.
- **search_jobs(position, location, page)**: Build URL, `driver.get(url)`, human sleep, random scroll; returns True/False.
- **scroll_job_list()**: Find `.jobs-search-results-list`, scroll gradually to load more cards.
- **get_job_cards()**: Scroll list, find `//div[@data-job-id]`, skip if id in `applied_job_ids` or card text contains "Applied" or company in blacklist; return list of `{ "id", "element" }`.
- **click_job_card(job_id)**: Dismiss modals, find card by `data-job-id`, scroll to it, click.
- **_dismiss_modals()**: Click discard/close if present.
- **get_job_title_and_company()**: Multiple CSS selectors for title and company in job details panel.
- **has_easy_apply_button()**: Wait 5s for button containing "Easy Apply" and class `jobs-apply-button`.
- **get_easy_apply_button()**: Same, returns element.

### 3.5 `application.py` — Form Filling and Submission

- **DailyLimitReachedException**: Raised when LinkedIn daily application limit is detected; main loop catches and exits.
- **AIQuestionAnswerer**:
  - **_load_resume()**: Find PDF in assets/ or root, parse with pypdf, store text in `resume_text`.
  - **get_smart_answer(question_text, context)**: If OpenAI client: try `_get_ai_answer`; if None, try `_get_fallback_answer` (salary/rate from context, "Prefer not to say" for demographic questions); otherwise return None (triggers human/validation path).
  - **_get_ai_answer()**: Prompt with resume excerpt + rules: short answers, yes/no, years from resume; output "REQUIRES_HUMAN_INPUT" if uncertain; call `chat.completions.create` (gpt-3.5-turbo, low temperature).
- **JobApplication**:
  - **__init__**: Holds driver, config, dry_run; creates `AIQuestionAnswerer`, output CSV path, `QAMemoryManager("qa_memory.csv")`, runs `deduplicate_memory()`.
  - **apply_to_job(job_id, job_title, company)**: `_click_easy_apply()` (may raise DailyLimitReachedException); `_fill_application_form()`; log to CSV; return "success" | "failed".
  - **_check_rate_limit()**: After Easy Apply click, check page source and visible elements for phrases like "limit daily submissions", "apply tomorrow"; raise `DailyLimitReachedException` if found.
  - **_click_easy_apply()**: Find and click Easy Apply; if button not found (TimeoutException), check body text for daily limit ("soft block") and raise same exception.
  - **_fill_application_form()**: Loop (max 15): fill phone, uploads, `_answer_questions()`; `_handle_validation_errors_with_learning()` (blocking; if False, discard and return False); `_get_next_action()`; if "submit", final validation then `_submit_application()`; if "next", `_click_next()` (or handle unknown questions); if "review", `_click_review()`.
  - **_answer_questions()**: Find `.jobs-easy-apply-form-section__grouping`; for each group get question via `_extract_question_text`; lookup in `qa_manager`; if missing, try AI, then optionally save to memory; fill with `_fill_field_with_answer` or leave blank (validation will catch).
  - **_extract_question_text(group)**: Multiple strategies with noise filter: aria-label, aria-labelledby, legend, LinkedIn header classes, label, text fallback; `_clean_question_text` removes "Required", "*", etc.
  - **_fill_field_with_answer(group, answer)**: Text input, radio (match value/label), select (exact/partial/first option).
  - **_detect_validation_errors()**: Find `.artdeco-inline-feedback--error` (and similar), get parent form group, use `_extract_question_text` for field_label; return list of { element, message, field_label }.
  - **_handle_validation_errors_with_learning()**: If errors, print and block on `input()`; then `_bulk_scrape_form_inputs()` to learn all visible Q&A; re-check errors; return True only if none left (or user skipped).
  - **_bulk_scrape_form_inputs()**: Iterate form sections, extract question/answer, call `qa_manager.learn_answer`.
  - **_get_next_action()**: Precedence submit → review → next (by button presence).
  - **_submit_application()**: In dry_run, discard and return True. If `require_submission_confirmation`, prompt user. Then `_handle_submit_step()`.
  - **_handle_submit_step()**: Retry loop: wait submit button; if disabled, `_pause_for_user_intervention`; `_force_click_button` (click then JS click fallback); `_verify_post_click_state` (success / discard_popup / still_on_form); on discard popup try cancel and retry.
  - **_discard_application()**: Dismiss/close modal, click Discard if confirmation appears.
  - **_log_application()**: Append row to CSV (timestamp, job_id, job_title, company, attempted, result).
  - **_save_crash_dump(reason)**: Write `crash_dumps/crash_dump_<timestamp>.html` with page source.

### 3.6 `qa_manager.py` — Q&A Memory

- **QAMemoryManager(memory_file)**: CSV with columns `question_text`, `answer_text`. Create file if missing; load into dict `memory` (normalized key → answer).
- **_normalize_text(text)**: Lowercase, strip, single spaces, remove `?`, `:`, `*`.
- **lookup_answer(question)**: Normalize; exact key lookup; if not found and `thefuzz` available, `process.extractOne` with 90% threshold; return answer or None.
- **learn_answer(question, answer)**: Normalize, update `memory`, rewrite entire CSV (deduplication by key).
- **deduplicate_memory()**: Reload from file (dict dedupes), rewrite CSV.
- **prompt_user_for_answer(question)**: Print question, input(); return (answer, should_skip). (Used conceptually; actual blocking prompts are in application.py for validation and unknown questions.)

### 3.7 `utils.py` — Stealth and Helpers

- **StealthUtils.human_sleep(min, max)**: `time.sleep(random.uniform(min, max))`.
- **StealthUtils.type_like_human(element, text)**: Clear, then send_keys char-by-char with small random delay.
- **StealthUtils.smooth_scroll_to_element(driver, element)**: `scrollIntoView({ behavior: 'smooth', block: 'center' })`.
- **StealthUtils.random_scroll(driver, element)**: Scroll page or element by random amount.
- **DateUtils.get_time_ago_filter(days)**: Map 1/7/30 days to LinkedIn f_TPR values (used in job_search URL building via config).

### 3.8 `logger.py`

- **get_logger()**: Returns module logger (configured once); used by all modules.

---

## 4. Key Algorithms and Patterns

### 4.1 Search URL Construction

All filters are encoded in the URL so no filter UI interaction is needed:

- **f_AL=true**: Easy Apply only.
- **f_TPR**: `r86400` (24h), `r604800` (week), `r2592000` (month).
- **f_WT**: Comma-separated: 1=onsite, 2=remote, 3=hybrid.
- **f_E**: Comma-separated: 1=Internship … 6=Executive (see job_search.py map).
- **keywords**, **location**, **start** (pagination).

### 4.2 Question-Answer Pipeline

1. **Extract question**: From form group via aria-label, legend, LinkedIn classes, label, or text; clean and reject noise ("please make a selection", "required", etc.).
2. **Lookup**: QAMemoryManager lookup (exact then fuzzy ≥90%).
3. **If missing**: AI (with resume context) if key present; if AI returns value, save to memory and fill.
4. **If still missing**: Leave blank → validation fails → `_handle_validation_errors_with_learning` pauses, user fixes, bulk scrape into memory.

### 4.3 Validation and Learning

- **Detection**: `.artdeco-inline-feedback--error` and similar; associate error with parent form group and use same `_extract_question_text` for consistent field label.
- **Blocking**: Before "Next" and before "Submit", call `_handle_validation_errors_with_learning`. If any error remains and user did not skip, do not proceed.
- **Learning**: After user fixes, `_bulk_scrape_form_inputs` walks all visible form sections, extracts question + answer, calls `qa_manager.learn_answer`. No need to map error message to single field.

### 4.4 Rate Limiting (LinkedIn Daily Limit)

- **After Easy Apply click**: `_check_rate_limit()` scans page source and visible text for "limit daily submissions", "apply tomorrow", etc.
- **If button missing**: Treat as possible "soft block"; check same phrases in body text; if found, raise `DailyLimitReachedException`.
- **Effect**: Main loop catches and exits cleanly, telling user to try tomorrow.

### 4.5 Stealth and Robustness

- Undetected Chrome, CDP to hide webdriver, random user-agent and human-like delays.
- Clicks: normal click first, then JS click fallback.
- Submit: verify post-click state (success vs discard popup vs still on form); retry with user intervention if needed.

---

## 5. Configuration and Environment

### config.yaml (Representative)

- **phone_number**, **salary**, **rate**
- **positions**: list of job title keywords
- **locations**: list of location strings
- **search.filters.date_posted**: "24h" | "week" | "month" | "any"
- **search.filters.workplace_type**: list of "remote", "hybrid", "onsite"
- **experience_level**: list of "Associate", "Mid-Senior level", etc.
- **uploads**: map e.g. Resume/Cover Letter to file paths
- **output_filename**: list (first used) or string
- **blacklist**, **blackListTitles**: lists
- **require_submission_confirmation**: bool
- **max_search_time**: seconds

### .env (Required / Optional)

- **LINKEDIN_USERNAME**, **LINKEDIN_PASSWORD** (required)
- **OPENAI_API_KEY** (optional; enables AI answers)

### Output and Data Files

- **output/applications.csv**: timestamp, job_id, job_title, company, attempted, result
- **qa_memory.csv**: question_text, answer_text (created under project root or path given to QAMemoryManager)
- **crash_dumps/crash_dump_*.html**: HTML snapshots on validation/submit failures

---

## 6. Dependencies (requirements.txt)

- **undetected-chromedriver**, **selenium**: browser automation
- **PyYAML**, **python-dotenv**: config
- **openai**: AI answers
- **pypdf**: resume PDF parsing
- **thefuzz**, **python-Levenshtein**: fuzzy Q&A matching
- **beautifulsoup4**, **lxml**, **pandas**, **packaging**: used elsewhere or by dependencies

---

## 7. Entry Points and CLI

- **Run**: `python -m src.main` or `python -m src.main --config custom.yaml --dry-run --headless`
- **Entry**: `main()` in `main.py` parses args, validates config path, instantiates `LinkedInEasyApplyBot`, calls `run()`.

---

## 8. Extension Points and Pitfalls (for LLMs)

- **New form field types**: Extend `_fill_field_with_answer` (e.g. date pickers, multi-select) and ensure question extraction covers new structures.
- **New filters**: Add URL params in `job_search.build_search_url` and corresponding config properties in `config.py`.
- **Different job list DOM**: Adjust selectors in `get_job_cards` and `click_job_card` (e.g. `data-job-id`, `.jobs-search-results-list`).
- **Q&A memory path**: `QAMemoryManager` is constructed with `"qa_memory.csv"` in application.py; path is relative to CWD unless changed.
- **Resume path**: AI answerer discovers PDF via globs in project root and `assets/`; ensure path exists or AI runs without context.
- **Rate limit wording**: If LinkedIn changes copy, update `_check_rate_limit` and `_click_easy_apply` phrase lists.
- **Submit button**: Identified by `aria-label*='Submit application'`; if LinkedIn changes, update `_find_submit_button` and related selectors.

---

## 9. Glossary

- **Easy Apply**: LinkedIn one-click application flow (modal form, no external redirect).
- **Constant vs variable filters**: In this codebase, all filters are variable per search and encoded in URL (no separate “constant” UI step).
- **Dry run**: Applications simulated; form filled but submission replaced by discard.
- **Q&A memory**: Persistent CSV of question → answer used to auto-fill repeated application questions.
- **Bulk scrape**: After user fixes validation errors, reading all visible form fields and saving to Q&A memory.
- **Daily limit**: LinkedIn cap on Easy Apply submissions per day; bot detects and stops to avoid looking suspicious.

---

This summary should give another LLM enough context to reason about the project, locate code for a given behavior, and implement or modify features consistently with the existing design.
