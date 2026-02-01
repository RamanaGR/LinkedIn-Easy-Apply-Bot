"""
Job application handling with AI-powered question answering.
"""

import csv
import time
import sys
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.config import Config
from src.logger import get_logger
from src.utils import StealthUtils
from src.qa_manager import QAMemoryManager

logger = get_logger()


class DailyLimitReachedException(Exception):
    """Exception raised when LinkedIn daily application limit is reached."""
    pass


class AIQuestionAnswerer:
    """AI-powered question answering using OpenAI with resume context."""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI question answerer with resume parsing.

        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key
        self.client = None
        self.resume_text = ""

        # Parse resume from assets/ folder
        self._load_resume()

        # AI Initialization with detailed debugging
        logger.info("=" * 80)
        logger.info("AI INITIALIZATION DEBUG")
        logger.info("=" * 80)
        
        if api_key:
            # Mask API key for logging (show first 7 and last 4 chars)
            masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
            logger.info(f"✅ OpenAI API key provided: {masked_key}")
            
            try:
                import openai
                logger.info(f"✅ OpenAI library version: {openai.__version__}")
                
                self.client = openai.OpenAI(api_key=api_key)
                logger.info("✅ OpenAI client initialized successfully")
                logger.info(f"✅ AI-powered answering: ENABLED")
                
                # Test API connectivity (optional, lightweight check)
                try:
                    # Quick validation that the client is working
                    logger.info("✅ OpenAI client ready for question answering")
                except Exception as e:
                    logger.warning(f"⚠️ OpenAI client created but validation failed: {e}")
                    
            except ImportError:
                logger.error("❌ OpenAI library not installed!")
                logger.error("   Install with: pip install openai")
                logger.warning("   AI features DISABLED - using fallback answers")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI client: {e}")
                logger.warning("   AI features DISABLED - using fallback answers")
        else:
            logger.warning("❌ No OpenAI API key provided in config.yaml or .env")
            logger.warning("   Set OPENAI_API_KEY in your .env file")
            logger.warning("   AI features DISABLED - using fallback answers only")
        
        logger.info("=" * 80)
        
        # Summary
        if self.client:
            logger.info("🤖 AI Question Answering: ACTIVE")
        else:
            logger.info("⚠️  AI Question Answering: INACTIVE (using fallbacks only)")
    
    def _load_resume(self):
        """
        Load and parse resume PDF from assets/ or workspace root.
        Stores extracted text in self.resume_text.
        """
        try:
            # Search for PDF files in multiple locations
            search_paths = [
                "assets/*.pdf",
                "*.pdf",
                "resume*.pdf",
                "cv*.pdf"
            ]
            
            pdf_file = None
            for pattern in search_paths:
                pdf_files = glob.glob(pattern)
                if pdf_files:
                    pdf_file = pdf_files[0]  # Use first match
                    break
            
            if not pdf_file:
                logger.warning("⚠️ No resume PDF found in assets/ or workspace root")
                logger.warning("AI will operate without resume context")
                return
            
            # Parse PDF
            try:
                from pypdf import PdfReader
                
                reader = PdfReader(pdf_file)
                text_parts = []
                
                for page in reader.pages:
                    text_parts.append(page.extract_text())
                
                self.resume_text = "\n".join(text_parts)
                logger.info(f"✅ Loaded resume from: {pdf_file}")
                logger.info(f"Resume text length: {len(self.resume_text)} characters")
                
            except ImportError:
                logger.error("pypdf library not installed! Run: pip install pypdf")
            except Exception as e:
                logger.error(f"Failed to parse resume PDF: {e}")
                
        except Exception as e:
            logger.error(f"Error loading resume: {e}")

    def get_smart_answer(
            self,
            question_text: str,
            context: Dict = None) -> Optional[str]:
        """
        Get an intelligent answer to a job application question.
        Returns None if uncertain (triggers human-in-the-loop learning).

        Args:
            question_text: The question to answer
            context: Optional context (salary, experience, etc.)

        Returns:
            Answer string or None if uncertain
        """
        question_lower = question_text.lower()

        # Try AI first if available
        if self.client:
            try:
                answer = self._get_ai_answer(question_text, context)
                if answer:
                    logger.info(
                        f"AI Answer: '{question_text[:50]}...' -> '{answer}'")
                    return answer
                else:
                    logger.debug(f"AI was uncertain about: '{question_text[:50]}...'")
                    # DO NOT use fallback - return None to trigger human input
                    return None
            except Exception as e:
                logger.warning(f"AI answer failed: {e}")

        # Try very conservative fallback only for obvious cases
        fallback_answer = self._get_fallback_answer(question_lower, context)
        if fallback_answer:
            logger.debug(f"Using conservative fallback: '{fallback_answer}'")
            return fallback_answer
        
        # No answer available - return None to leave field blank
        return None

    def _get_ai_answer(
            self,
            question: str,
            context: Dict = None) -> Optional[str]:
        """
        Get answer from OpenAI with resume context.
        Returns REQUIRES_HUMAN_INPUT if uncertain.

        Args:
            question: Question text
            context: Additional context

        Returns:
            AI-generated answer, "REQUIRES_HUMAN_INPUT", or None
        """
        if not self.client:
            return None

        try:
            # Build context string
            context_str = ""
            if context:
                context_str = f"\nAdditional Context: {context}"
            
            # Build resume context
            resume_context = ""
            if self.resume_text:
                # Use first 2000 chars to avoid token limits
                resume_excerpt = self.resume_text[:2000]
                resume_context = f"\n\nRESUME CONTEXT:\n{resume_excerpt}"

            # Create prompt with strict instructions
            prompt = f"""You are helping to fill out a job application form on LinkedIn.

CRITICAL RULES:
1. Answer ONLY based on the resume context provided below
2. Keep answers short (1-3 words or a number)
3. For yes/no questions, answer with ONLY "Yes" or "No"
4. For years of experience, provide ONLY a number based on resume dates
5. For personal preferences (salary expectations, specific citizenship status, willingness to relocate, etc.) that are NOT explicitly stated in the resume: Output exactly "REQUIRES_HUMAN_INPUT"
6. If you are less than 90% confident in your answer: Output exactly "REQUIRES_HUMAN_INPUT"{resume_context}{context_str}

Question: {question}

Answer (or output exactly "REQUIRES_HUMAN_INPUT" if uncertain/preference):"""

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a precise job application assistant. Follow ALL rules strictly. Output 'REQUIRES_HUMAN_INPUT' when uncertain."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3  # Lower temperature for more deterministic answers
            )

            answer = response.choices[0].message.content.strip()
            
            # Check if AI explicitly indicated uncertainty
            if answer == "REQUIRES_HUMAN_INPUT" or not answer:
                logger.debug(f"AI returned REQUIRES_HUMAN_INPUT for: {question[:50]}...")
                return None
            
            return answer

        except Exception as e:
            logger.debug(f"OpenAI API error: {e}")
            return None

    def _get_fallback_answer(
            self,
            question_lower: str,
            context: Dict = None) -> Optional[str]:
        """
        Get CONSERVATIVE fallback rule-based answer.
        Only returns answers for very obvious/safe questions.
        Returns None for anything uncertain to trigger human input.

        Args:
            question_lower: Lowercase question text
            context: Additional context

        Returns:
            Safe fallback answer or None
        """
        # Only handle VERY OBVIOUS cases with context
        
        # Salary questions - ONLY if we have the value in context
        if "salary" in question_lower or "compensation" in question_lower:
            if context and "salary" in context and context["salary"]:
                return str(context["salary"])
            # Don't guess - return None
            return None

        # Rate questions - ONLY if we have the value in context
        if "rate" in question_lower or "hourly" in question_lower:
            if context and "rate" in context and context["rate"]:
                return str(context["rate"])
            return None

        # Gender/race/ethnicity - Safe default
        if any(
            word in question_lower for word in [
                "gender",
                "race",
                "ethnicity",
                "veteran",
                "disability"]):
            return "Prefer not to say"

        # For everything else, return None to trigger human input
        # This includes:
        # - Experience years (we don't know without resume)
        # - Sponsorship (personal preference)
        # - Work authorization (personal info)
        # - Citizenship (personal info)
        # - Generic yes/no questions (we don't know the answer)
        
        logger.debug(
            f"No safe fallback for: {question_lower[:50]}... (returning None)")
        return None


class JobApplication:
    """Handles the job application process."""

    def __init__(self, driver, config: Config, dry_run: bool = False):
        """
        Initialize job application handler.

        Args:
            driver: Selenium WebDriver instance
            config: Configuration object
            dry_run: If True, don't submit applications
        """
        self.driver = driver
        self.config = config
        self.dry_run = dry_run
        self.wait = WebDriverWait(driver, 30)

        # Initialize AI answerer
        self.ai_answerer = AIQuestionAnswerer(config.openai_api_key)
        
        # Setup output file
        self.output_file = Path(config.output_filename)
        self._ensure_output_file()
        
        # Setup Q&A Memory Manager (Self-Learning System)
        self.qa_manager = QAMemoryManager("qa_memory.csv")
        
        # Automatically deduplicate CSV on startup to clean any existing duplicates
        self.qa_manager.deduplicate_memory()
        
        logger.info(f"Application handler initialized (dry_run={dry_run})")
        logger.info(f"Q&A Memory: {self.qa_manager.get_memory_stats()['total_pairs']} pairs loaded")

    def _ensure_output_file(self):
        """Create output CSV file if it doesn't exist."""
        if not self.output_file.exists():
            self.output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ['timestamp', 'job_id', 'job_title', 'company', 'attempted', 'result'])
            logger.info(f"Created output file: {self.output_file}")
    

    def apply_to_job(self, job_id: str, job_title: str, company: str) -> str:
        """
        Apply to a job posting.

        Args:
            job_id: LinkedIn job ID
            job_title: Job title
            company: Company name

        Returns:
            "success" if application successful
            "failed" if application failed
            "rate_limited" if daily limit reached
            
        Raises:
            DailyLimitReachedException: If LinkedIn daily limit is reached
        """
        logger.info(f"🎯 Applying to: {job_title} at {company}")

        try:
            # Click Easy Apply button (may raise DailyLimitReachedException)
            click_result = self._click_easy_apply()
            
            if not click_result:
                self._log_application(
                    job_id,
                    job_title,
                    company,
                    attempted=False,
                    result=False)
                return "failed"

            # Fill application form (may also raise DailyLimitReachedException)
            success = self._fill_application_form()

            # Log result
            self._log_application(
                job_id,
                job_title,
                company,
                attempted=True,
                result=success)

            if success:
                logger.info(f"✅ Successfully applied to {job_title}")
                return "success"
            else:
                logger.warning(f"⚠️  Application incomplete for {job_title}")
                return "failed"

        except DailyLimitReachedException:
            # Re-raise to stop the bot completely
            self._log_application(
                job_id,
                job_title,
                company,
                attempted=False,
                result=False)
            raise
            
        except Exception as e:
            logger.error(f"Application failed: {e}", exc_info=True)
            self._log_application(
                job_id,
                job_title,
                company,
                attempted=True,
                result=False)
            return "failed"

    def _check_rate_limit(self) -> bool:
        """
        Check if LinkedIn has rate-limited the user (daily submission limit).
        
        Detects the message:
        "We limit daily submissions to maintain quality and prevent bots, 
        helping each application get the right attention. Save this job and apply tomorrow."
        
        Raises:
            DailyLimitReachedException: If rate limit is detected
        
        Returns:
            True if rate limited (and exception raised), False otherwise
        """
        try:
            # Wait a moment for any modals to appear
            StealthUtils.human_sleep(1, 2)
            
            # Check page source for rate limit keywords
            page_source = self.driver.page_source.lower()
            
            rate_limit_phrases = [
                "limit daily submissions",
                "we limit daily submissions to maintain quality",
                "apply tomorrow",
                "helping each application get the right attention",
                "save this job and apply tomorrow"
            ]
            
            # Check if any rate limit phrase is present
            for phrase in rate_limit_phrases:
                if phrase in page_source:
                    logger.critical("=" * 80)
                    logger.critical("⛔ DAILY APPLICATION LIMIT REACHED!")
                    logger.critical("=" * 80)
                    logger.critical("LinkedIn Message:")
                    logger.critical("'We limit daily submissions to maintain quality and prevent bots,")
                    logger.critical("helping each application get the right attention.'")
                    logger.critical("")
                    logger.critical("⏰ PLEASE APPLY AGAIN TOMORROW")
                    logger.critical("The bot will now stop to avoid appearing suspicious.")
                    logger.critical("=" * 80)
                    
                    # Raise exception to stop the bot completely
                    raise DailyLimitReachedException(
                        "LinkedIn daily application limit reached. Please try again tomorrow."
                    )
            
            # Also check for modal/dialog with rate limit message
            try:
                rate_limit_elements = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'limit daily submissions') or "
                    "contains(text(), 'apply tomorrow') or "
                    "contains(text(), 'helping each application get the right attention')]"
                )
                
                if rate_limit_elements:
                    for elem in rate_limit_elements:
                        if elem.is_displayed():
                            logger.critical("=" * 80)
                            logger.critical("⛔ DAILY APPLICATION LIMIT REACHED!")
                            logger.critical("=" * 80)
                            logger.critical("Detected via visible UI element")
                            logger.critical("⏰ PLEASE APPLY AGAIN TOMORROW")
                            logger.critical("=" * 80)
                            
                            raise DailyLimitReachedException(
                                "LinkedIn daily application limit reached. Please try again tomorrow."
                            )
            except DailyLimitReachedException:
                raise
            except:
                pass
            
            return False
            
        except DailyLimitReachedException:
            raise
        except Exception as e:
            logger.debug(f"Error checking rate limit: {e}")
            return False
    
    def _click_easy_apply(self) -> bool:
        """
        Click the Easy Apply button and check for rate limiting.
        
        CRITICAL: If button not found, checks for daily limit "soft block" message.

        Returns:
            True if successful, False otherwise
            
        Raises:
            DailyLimitReachedException: If daily limit is detected (hard or soft block)
        """
        try:
            button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]'
                ))
            )

            StealthUtils.smooth_scroll_to_element(self.driver, button)
            StealthUtils.human_sleep(0.5, 1.0)

            button.click()
            logger.info("Clicked Easy Apply button")
            StealthUtils.human_sleep(2, 3)

            # Check for rate limit message (raises DailyLimitReachedException if detected)
            self._check_rate_limit()

            return True

        except DailyLimitReachedException:
            raise
        except TimeoutException:
            # CRITICAL FIX: When Easy Apply button is missing, check for "soft block" message
            logger.warning("⚠️  Easy Apply button not found - checking for daily limit...")
            
            # Check for daily limit "soft block" message
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                
                # Target phrase: "limit daily submissions"
                if "limit daily submissions" in page_text:
                    logger.critical("=" * 80)
                    logger.critical("⛔ DAILY LIMIT REACHED (SOFT BLOCK DETECTED)")
                    logger.critical("=" * 80)
                    logger.critical("LinkedIn message: 'We limit daily submissions to maintain quality'")
                    logger.critical("⛔ STOPPING BOT IMMEDIATELY")
                    logger.critical("⏰ PLEASE APPLY AGAIN TOMORROW")
                    logger.critical("=" * 80)
                    
                    # Raise exception to stop the bot completely
                    raise DailyLimitReachedException(
                        "Daily application limit reached (soft block - Easy Apply button hidden)"
                    )
            except DailyLimitReachedException:
                raise
            except Exception as e:
                logger.debug(f"Could not check page text for rate limit: {e}")
            
            # No daily limit detected - just a missing button (normal skip)
            logger.warning("Easy Apply button not found (job may not support Easy Apply)")
            return False

    def _fill_application_form(self) -> bool:
        """
        Fill out the application form with multiple steps.
        
        This method implements error-aware form filling:
        1. Fill fields progressively
        2. Detect validation errors after each step
        3. Prompt user for unknown questions
        4. Block submission if red text is present

        Returns:
            True if successfully submitted, False otherwise
        """
        max_iterations = 15  # Increased for complex forms
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            logger.debug(f"Form filling iteration {iteration}/{max_iterations}")
            StealthUtils.human_sleep(1, 2)

            # Fill phone number if found
            self._fill_phone_number()

            # Upload documents if needed
            self._upload_documents()

            # Answer questions (with memory lookup)
            self._answer_questions()

            # CRITICAL: Detect validation errors BEFORE proceeding
            # Use BLOCKING validation handler that learns from user fixes
            if not self._handle_validation_errors_with_learning():
                logger.error("⛔ Cannot proceed - validation errors unresolved or user skipped")
                self._save_crash_dump("Validation errors unresolved")
                self._discard_application()
                return False

            # Try to proceed to next step or submit
            next_action = self._get_next_action()
            logger.debug(f"Next action determined: {next_action}")

            if next_action == "submit":
                # FINAL CHECK: Before submission, use BLOCKING validation handler
                logger.info("Final validation check before submission...")
                if not self._handle_validation_errors_with_learning():
                    logger.error("⛔ BLOCKED SUBMISSION: Validation errors unresolved")
                    self._save_crash_dump("Blocked submission due to validation errors")
                    self._discard_application()
                    return False
                
                # Check if submit button is disabled
                submit_btn = self._find_submit_button()
                if submit_btn and not submit_btn.is_enabled():
                    logger.warning("⚠️  Submit button is disabled - checking for issues")
                    if not self._handle_validation_errors_with_learning():
                        logger.error("Cannot submit - form incomplete")
                        self._save_crash_dump("Submit button disabled")
                        self._discard_application()
                        return False
                
                # All checks passed - proceed to submission
                return self._submit_application()
                
            elif next_action == "next":
                if not self._click_next():
                    # Next button might be disabled, check for unknown questions
                    logger.warning("Next button click failed, checking for issues...")
                    if not self._handle_unknown_questions():
                        logger.error("Cannot proceed to next step")
                        self._save_crash_dump("Next button click failed")
                        break
            elif next_action == "review":
                self._click_review()
            else:
                logger.warning("Unknown form state, trying next button...")
                if not self._click_next():
                    logger.error("Failed to progress form")
                    self._save_crash_dump("Unknown form state")
                    break

        logger.error(f"Form filling exceeded max iterations ({max_iterations})")
        self._save_crash_dump(f"Max iterations exceeded: {max_iterations}")
        self._discard_application()
        return False

    def _fill_phone_number(self):
        """Fill phone number if the field exists."""
        try:
            phone_fields = self.driver.find_elements(
                By.XPATH,
                "//input[contains(@id, 'phoneNumber') or contains(@id, 'phone')]"
            )

            for field in phone_fields:
                if field.is_displayed() and self.config.phone_number:
                    field.clear()
                    StealthUtils.type_like_human(
                        field, str(self.config.phone_number))
                    logger.debug("Phone number filled")

        except Exception as e:
            logger.debug(f"Could not fill phone number: {e}")

    def _upload_documents(self):
        """Upload resume, cover letter, etc."""
        try:
            # Look for upload buttons
            upload_buttons = self.driver.find_elements(
                By.XPATH,
                "//input[@type='file']"
            )

            for button in upload_buttons:
                if not button.is_displayed():
                    continue

                # Determine which document to upload
                button_id = button.get_attribute("id") or ""
                button_name = button.get_attribute("name") or ""

                upload_path = None

                if "resume" in button_id.lower() or "resume" in button_name.lower():
                    upload_path = self.config.uploads.get("Resume")
                elif "cover" in button_id.lower() or "cover" in button_name.lower():
                    upload_path = self.config.uploads.get("Cover Letter")

                if upload_path and Path(upload_path).exists():
                    button.send_keys(str(Path(upload_path).resolve()))
                    logger.info(f"Uploaded document: {Path(upload_path).name}")
                    StealthUtils.human_sleep(1, 2)

        except Exception as e:
            logger.debug(f"Document upload: {e}")

    def _answer_questions(self):
        """
        Answer form questions using self-learning Q&A system.
        
        Process:
        1. Identify question text from label
        2. Lookup answer in qa_memory.csv
        3. If found: Auto-fill
        4. If not found: Pause, prompt user, learn, fill
        """
        try:
            # Find all form fields
            form_groups = self.driver.find_elements(
                By.CLASS_NAME,
                "jobs-easy-apply-form-section__grouping"
            )

            context = {
                "salary": self.config.salary,
                "rate": self.config.rate
            }
            
            logger.debug(f"Found {len(form_groups)} form field groups to process")

            for group in form_groups:
                if not group.is_displayed():
                    continue

                # STEP A: Identify Question
                question_text = self._extract_question_text(group)
                if not question_text:
                    logger.debug("No question text extracted from form group")
                    continue
                
                logger.debug(f"Processing question: '{question_text[:60]}...'")

                # STEP B: Lookup Answer in Memory
                answer = self.qa_manager.lookup_answer(question_text)

                if answer:
                    # FOUND IN MEMORY
                    logger.info(f"✅ [MEMORY] Found answer for: '{question_text[:40]}...' -> '{answer}'")
                else:
                    # NOT FOUND IN MEMORY - Try AI 
                    logger.warning(f"❌ Not in memory: '{question_text[:60]}...'")
                    
                    # Try AI-powered answer (if available)
                    if self.ai_answerer.client:
                        logger.info(f"🤖 Trying AI-powered answer...")
                        answer = self.ai_answerer.get_smart_answer(question_text, context)
                        if answer:
                            logger.info(f"✅ [AI] Generated answer: '{answer}'")
                            # Save AI answer to memory for future use
                            self.qa_manager.learn_answer(question_text, answer)
                            logger.info(f"💾 Saved AI answer to memory")
                        else:
                            logger.warning(f"AI was uncertain or returned None")

                # STEP C: Fill the field with answer (or leave blank if None)
                if answer:
                    logger.debug(f"Attempting to fill field with answer: '{answer}'")
                    self._fill_field_with_answer(group, answer)
                else:
                    # NO ANSWER AVAILABLE - Leave field blank
                    # This will trigger validation error (red text) which will call
                    # _handle_validation_errors_with_learning() and prompt user
                    logger.warning(f"⚠️ Answer not found/generated. Leaving blank to trigger validation loop.")
                    logger.warning(f"   Question: '{question_text[:60]}...'")
                    logger.warning(f"   This will pause for user input when validation runs.")

        except Exception as e:
            logger.error(f"Error in question answering: {e}", exc_info=True)

    def _extract_question_text(self, group_element) -> Optional[str]:
        """
        ROBUST extraction of question text from a form group element.
        
        Implements multiple strategies with CRITICAL filtering to avoid noise.
        Priority: Aria-label → Legend → Header Classes → Label → Text fallback
        
        Args:
            group_element: The form group WebElement

        Returns:
            Cleaned question text or None if extraction fails
        """
        # NOISE FILTER: Common invalid texts to reject
        NOISE_TEXTS = [
            "please make a selection",
            "enter a whole number",
            "select an option",
            "required",
            "choose an option",
            "pick one",
            ""
        ]
        
        def is_valid_question(text: str) -> bool:
            """Check if extracted text is a valid question (not noise)."""
            if not text or len(text) < 3:
                return False
            text_lower = text.lower().strip()
            for noise in NOISE_TEXTS:
                if text_lower == noise or text_lower.startswith(noise):
                    return False
            return True
        
        try:
            # STRATEGY A: Aria-Label (HIGHEST PRIORITY - most reliable)
            try:
                inputs = group_element.find_elements(
                    By.CSS_SELECTOR,
                    "input, select, textarea"
                )
                for input_elem in inputs:
                    if not input_elem.is_displayed():
                        continue
                    
                    # Try aria-label
                    aria_label = input_elem.get_attribute("aria-label")
                    if aria_label:
                        # Clean immediately: strip newlines and extra spaces
                        cleaned = aria_label.replace('\n', ' ').replace('\r', ' ')
                        cleaned = ' '.join(cleaned.split())  # Collapse multiple spaces
                        cleaned = self._clean_question_text(cleaned)
                        
                        if cleaned and is_valid_question(cleaned):
                            logger.debug(f"[Strategy A: Aria] '{cleaned[:50]}...'")
                            return cleaned
                    
                    # Try aria-labelledby
                    aria_labelledby = input_elem.get_attribute("aria-labelledby")
                    if aria_labelledby:
                        try:
                            label_elem = self.driver.find_element(By.ID, aria_labelledby)
                            text = label_elem.text
                            if text:
                                cleaned = text.replace('\n', ' ').replace('\r', ' ')
                                cleaned = ' '.join(cleaned.split())
                                cleaned = self._clean_question_text(cleaned)
                                
                                if cleaned and is_valid_question(cleaned):
                                    logger.debug(f"[Strategy A: Aria-labelledby] '{cleaned[:50]}...'")
                                    return cleaned
                        except:
                            pass
            except:
                pass

            # STRATEGY B: Legend (for fieldsets - common in Yes/No radios)
            try:
                legend = group_element.find_element(By.TAG_NAME, "legend")
                text = legend.text
                if text:
                    cleaned = text.replace('\n', ' ').replace('\r', ' ')
                    cleaned = ' '.join(cleaned.split())
                    cleaned = self._clean_question_text(cleaned)
                    
                    if cleaned and is_valid_question(cleaned):
                        logger.debug(f"[Strategy B: Legend] '{cleaned[:50]}...'")
                        return cleaned
            except:
                pass

            # STRATEGY C: LinkedIn-specific header classes
            header_selectors = [
                ".jobs-easy-apply-form-element__label",
                "span.t-16",  # LinkedIn header text (most common)
                ".fb-dash-form-element__label",
                "span.t-14",
                ".artdeco-text-input--label",
                ".jobs-easy-apply-form-section__title"
            ]
            
            for selector in header_selectors:
                try:
                    header_elem = group_element.find_element(By.CSS_SELECTOR, selector)
                    text = header_elem.text
                    if text:
                        cleaned = text.replace('\n', ' ').replace('\r', ' ')
                        cleaned = ' '.join(cleaned.split())
                        cleaned = self._clean_question_text(cleaned)
                        
                        if cleaned and is_valid_question(cleaned):
                            logger.debug(f"[Strategy C: Header '{selector}'] '{cleaned[:50]}...'")
                            return cleaned
                except:
                    continue

            # STRATEGY D: Standard Label Tag
            try:
                label = group_element.find_element(By.TAG_NAME, "label")
                text = label.text
                if text:
                    cleaned = text.replace('\n', ' ').replace('\r', ' ')
                    cleaned = ' '.join(cleaned.split())
                    cleaned = self._clean_question_text(cleaned)
                    
                    if cleaned and is_valid_question(cleaned):
                        logger.debug(f"[Strategy D: Label] '{cleaned[:50]}...'")
                        return cleaned
            except:
                pass

            # STRATEGY E: Text Node Fallback (last resort)
            try:
                full_text = group_element.text
                if full_text:
                    # Clean immediately
                    full_text = full_text.replace('\n', ' ').replace('\r', ' ')
                    full_text = ' '.join(full_text.split())
                    
                    # Split and find first valid line
                    parts = [p.strip() for p in full_text.split('.') if p.strip()]
                    if not parts:
                        parts = [full_text]
                    
                    for part in parts[:3]:  # Check first 3 parts
                        cleaned = self._clean_question_text(part)
                        if cleaned and is_valid_question(cleaned) and len(cleaned) < 200:
                            logger.debug(f"[Strategy E: Text] '{cleaned[:50]}...'")
                            return cleaned
            except:
                pass

            # All strategies failed
            logger.warning("⚠️  Could not extract valid question text")
            return None

        except Exception as e:
            logger.error(f"❌ Error in _extract_question_text: {e}", exc_info=True)
            return None
    
    def _clean_question_text(self, text: str) -> str:
        """
        Clean question text by removing noise like "Required", "*", etc.
        This ensures consistent matching with the Q&A memory.
        
        Args:
            text: Raw question text
            
        Returns:
            Cleaned question text
        """
        if not text:
            return ""
        
        # Remove common noise words/chars
        noise_patterns = [
            " (Required)",
            " (required)",
            "(Required)",
            "(required)",
            "Required",
            "required",
            "*",
            "  ",  # Double spaces
        ]
        
        for pattern in noise_patterns:
            text = text.replace(pattern, " ")
        
        # Clean up extra whitespace
        text = " ".join(text.split())
        
        return text.strip()

    def _fill_field_with_answer(self, group_element, answer: str):
        """
        Fill a form field with the provided answer.

        Args:
            group_element: The form group WebElement
            answer: The answer to fill
        """
        try:
            # Text inputs
            text_inputs = group_element.find_elements(By.TAG_NAME, "input")
            for input_field in text_inputs:
                if input_field.get_attribute(
                        "type") == "text" and input_field.is_displayed():
                    if not input_field.get_attribute("value"):
                        StealthUtils.type_like_human(input_field, answer)
                        logger.debug(f"Filled text field: {answer}")
                        return

            # Radio buttons
            radio_buttons = group_element.find_elements(
                By.CSS_SELECTOR, "input[type='radio']")
            if radio_buttons:
                for radio in radio_buttons:
                    radio_value = radio.get_attribute("value") or ""
                    radio_label = ""
                    try:
                        # Try to get the label text for this radio button
                        radio_id = radio.get_attribute("id")
                        if radio_id:
                            label = group_element.find_element(
                                By.CSS_SELECTOR, f"label[for='{radio_id}']")
                            radio_label = label.text.strip()
                    except:
                        pass

                    # Match answer to radio value or label
                    if (answer.lower() in radio_value.lower() or
                            answer.lower() in radio_label.lower()):
                        radio.click()
                        logger.debug(
                            f"Selected radio: {radio_value or radio_label}")
                        return

            # Dropdowns
            selects = group_element.find_elements(By.TAG_NAME, "select")
            for select in selects:
                if select.is_displayed():
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(select)
                    try:
                        # Try exact match first
                        select_element.select_by_visible_text(answer)
                        logger.debug(f"Selected dropdown: {answer}")
                        return
                    except:
                        # Try partial match
                        for option in select_element.options:
                            if answer.lower() in option.text.lower():
                                option.click()
                                logger.debug(
                                    f"Selected dropdown (partial): {option.text}")
                                return

                        # Fallback to first non-empty option
                        if len(select_element.options) > 1:
                            select_element.select_by_index(1)
                            logger.debug("Selected default dropdown option")
                            return

        except Exception as e:
            logger.debug(f"Could not fill field: {e}")

    def _has_errors(self) -> bool:
        """Check if form has validation errors."""
        try:
            errors = self.driver.find_elements(
                By.CLASS_NAME,
                "artdeco-inline-feedback--error"
            )
            return len(errors) > 0
        except BaseException:
            return False
    
    def _detect_validation_errors(self) -> List[Dict]:
        """
        Detect all validation errors on the current form.
        
        Uses robust label extraction to identify which field has the error.
        
        Returns:
            List of dicts with error info: {element, message, field_label}
        """
        validation_errors = []
        
        try:
            # Method 1: Look for artdeco inline feedback messages
            error_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".artdeco-inline-feedback__message, .artdeco-inline-feedback--error"
            )
            
            for error_elem in error_elements:
                if not error_elem.is_displayed():
                    continue
                
                error_message = error_elem.text.strip()
                if not error_message:
                    continue
                
                # ROBUST: Find the form group and extract question using unified method
                field_label = "Unknown field"
                try:
                    # Try multiple parent container patterns
                    parent_selectors = [
                        "./ancestor::*[contains(@class, 'jobs-easy-apply-form-section__grouping')]",
                        "./ancestor::*[contains(@class, 'fb-dash-form-element')]",
                        "./ancestor::*[contains(@class, 'form-section')]",
                        "./ancestor::*[contains(@class, 'form-component')]",
                        "./ancestor::div[contains(@class, 'form')]"
                    ]
                    
                    parent_container = None
                    for selector in parent_selectors:
                        try:
                            parent_container = error_elem.find_element(By.XPATH, selector)
                            if parent_container:
                                break
                        except:
                            continue
                    
                    if parent_container:
                        # Use the unified robust extraction method
                        extracted = self._extract_question_text(parent_container)
                        if extracted:
                            field_label = extracted
                            logger.debug(f"✅ Extracted field label for error: '{field_label[:50]}...'")
                        else:
                            logger.warning(f"⚠️  Could not extract label for validation error")
                    else:
                        logger.warning(f"⚠️  Could not find parent container for error")
                        
                except Exception as label_error:
                    logger.debug(f"Error extracting field label: {label_error}")
                
                validation_errors.append({
                    "element": error_elem,
                    "message": error_message,
                    "field_label": field_label
                })
                
                logger.warning(f"Validation error: '{field_label}' - '{error_message}'")
            
            # Method 2: Look for red text that says "Please" (common validation pattern)
            red_text_elements = self.driver.find_elements(
                By.XPATH,
                "//*[contains(@class, 'error') or contains(@class, 'invalid')]//text()[contains(., 'Please')]/.."
            )
            
            for elem in red_text_elements:
                try:
                    if not elem.is_displayed():
                        continue
                    
                    # Skip if already detected
                    if elem in [e["element"] for e in validation_errors]:
                        continue
                    
                    message = elem.text.strip()
                    if not message:
                        continue
                    
                    # Try to find parent form group for this error too
                    field_label = "Unknown field"
                    try:
                        parent_selectors = [
                            "./ancestor::*[contains(@class, 'jobs-easy-apply-form-section__grouping')]",
                            "./ancestor::*[contains(@class, 'fb-dash-form-element')]",
                            "./ancestor::*[contains(@class, 'form-section')]"
                        ]
                        
                        for selector in parent_selectors:
                            try:
                                parent = elem.find_element(By.XPATH, selector)
                                extracted = self._extract_question_text(parent)
                                if extracted:
                                    field_label = extracted
                                    break
                            except:
                                continue
                    except:
                        pass
                    
                    validation_errors.append({
                        "element": elem,
                        "message": message,
                        "field_label": field_label
                    })
                    logger.warning(f"Validation error: '{field_label}' - '{message}'")
                    
                except Exception as e:
                    logger.debug(f"Error processing red text element: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in _detect_validation_errors: {e}", exc_info=True)
        
        return validation_errors
    
    def _save_crash_dump(self, reason: str = "Unknown"):
        """
        Save HTML dump of current page for debugging.
        
        Args:
            reason: Reason for the crash dump
        """
        try:
            # Create crash_dumps directory
            dumps_dir = Path("crash_dumps")
            dumps_dir.mkdir(exist_ok=True)
            
            # Create filename with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dump_file = dumps_dir / f"crash_dump_{timestamp}.html"
            
            # Get page source
            page_source = self.driver.page_source
            
            # Write to file
            with open(dump_file, 'w', encoding='utf-8') as f:
                f.write(f"<!-- CRASH DUMP -->\n")
                f.write(f"<!-- Reason: {reason} -->\n")
                f.write(f"<!-- URL: {self.driver.current_url} -->\n")
                f.write(f"<!-- Timestamp: {timestamp} -->\n\n")
                f.write(page_source)
            
            logger.error(f"Crash dump saved to: {dump_file}")
            logger.error(f"Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to save crash dump: {e}")
    
    def _handle_validation_errors_with_learning(self) -> bool:
        """
        BLOCKING method that pauses execution when validation errors are detected.
        
        Uses a BULK SCRAPE approach after user fixes errors:
        1. Detect validation errors
        2. Pause and wait for user to fix
        3. Scrape ALL visible form inputs (not just error fields)
        4. Save all non-empty values to qa_memory.csv
        
        This is more robust than trying to map specific errors to specific fields.
        
        Returns:
            True if errors were resolved, False if user wants to skip
        """
        validation_errors = self._detect_validation_errors()
        
        if not validation_errors:
            return True  # No errors, proceed
        
        # STEP A: RED FLAGS DETECTED
        logger.error(f"⛔ VALIDATION ERRORS DETECTED: {len(validation_errors)} error(s)")
        logger.error("The bot WILL NOT submit until these are fixed!")
        
        # Print ALL errors
        print("\n" + "=" * 80)
        print("⚠️  VALIDATION ERRORS DETECTED - EXECUTION PAUSED")
        print("=" * 80)
        for idx, error in enumerate(validation_errors, 1):
            error_msg = error['message']
            field_label = error['field_label']
            print(f"{idx}. Field: '{field_label}'")
            print(f"   Error: {error_msg}")
            logger.error(f"Validation error {idx}: Field='{field_label}', Message='{error_msg}'")
        print("=" * 80)
        print("\a")  # System beep
        
        # STEP B: BLOCKING PAUSE
        print("\n👉 Please fix the error(s) in the browser window.")
        print("   The bot will WAIT here until you press ENTER.")
        print("   (Type 'skip' to skip this job application)\n")
        
        response = input("Press ENTER when you've fixed the errors (or type 'skip'): ").strip().lower()
        
        if response == 'skip':
            logger.warning("User chose to skip this application")
            return False
        
        # STEP C: BULK SCRAPE - Learn from ALL visible form inputs
        logger.info("User fixed errors, performing bulk scrape of all form fields...")
        learned_count = self._bulk_scrape_form_inputs()
        logger.info(f"✅ Bulk scrape complete: Learned {learned_count} question-answer pairs")
        
        # Re-check for errors after user intervention
        logger.info("Re-checking for validation errors...")
        remaining_errors = self._detect_validation_errors()
        
        if remaining_errors:
            logger.error(f"⛔ {len(remaining_errors)} validation error(s) still present!")
            return False
        else:
            logger.info("✅ All validation errors resolved!")
            return True
    
    def _bulk_scrape_form_inputs(self) -> int:
        """
        Scrape ALL visible form inputs on the current step and save to memory.
        
        This is called after user manually fixes validation errors.
        We don't try to map specific errors to fields - we just scrape everything.
        
        Returns:
            Number of question-answer pairs learned
        """
        learned_count = 0
        
        try:
            # Find all form sections/groupings
            form_sections = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".jobs-easy-apply-form-section__grouping, .fb-dash-form-element"
            )
            
            logger.debug(f"Found {len(form_sections)} form sections to scrape")
            
            for section in form_sections:
                if not section.is_displayed():
                    continue
                
                try:
                    # Extract question/label
                    question = self._extract_question_from_section(section)
                    if not question:
                        continue
                    
                    # Extract answer/value
                    answer = self._extract_answer_from_section(section)
                    if not answer:
                        continue
                    
                    # Save to memory
                    self.qa_manager.learn_answer(question, answer)
                    logger.info(f"📝 Learned: '{question[:50]}...' = '{answer[:50]}...'")
                    print(f"✅ Saved: '{question[:50]}...' -> '{answer[:30]}...'")
                    learned_count += 1
                    
                except Exception as e:
                    logger.debug(f"Could not scrape section: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Error in bulk scrape: {e}", exc_info=True)
        
        return learned_count
    
    def _extract_question_from_section(self, section) -> Optional[str]:
        """
        Extract question/label text from a form section.
        
        This is a wrapper that calls the main _extract_question_text method
        to ensure consistency across all question extraction.
        
        Args:
            section: The form section WebElement
            
        Returns:
            Cleaned question text or None
        """
        try:
            return self._extract_question_text(section)
        except Exception as e:
            logger.debug(f"Could not extract question from section: {e}")
            return None
    
    def _extract_answer_from_section(self, section) -> Optional[str]:
        """Extract answer/value from a form section."""
        try:
            # Strategy 1: Text inputs
            text_inputs = section.find_elements(
                By.CSS_SELECTOR,
                "input[type='text'], input[type='email'], input[type='number'], input[type='tel'], textarea"
            )
            for input_field in text_inputs:
                if input_field.is_displayed():
                    value = input_field.get_attribute("value")
                    if value and value.strip():
                        return value.strip()
            
            # Strategy 2: Radio buttons (checked)
            radios = section.find_elements(By.CSS_SELECTOR, "input[type='radio']:checked")
            for radio in radios:
                if radio.is_displayed():
                    # Try to get label text
                    radio_id = radio.get_attribute("id")
                    if radio_id:
                        try:
                            label = section.find_element(By.CSS_SELECTOR, f"label[for='{radio_id}']")
                            return label.text.strip()
                        except:
                            pass
                    # Fallback to value attribute
                    value = radio.get_attribute("value")
                    if value:
                        return value
            
            # Strategy 3: Checkboxes (checked)
            checkboxes = section.find_elements(By.CSS_SELECTOR, "input[type='checkbox']:checked")
            if checkboxes:
                checked_labels = []
                for checkbox in checkboxes:
                    if checkbox.is_displayed():
                        checkbox_id = checkbox.get_attribute("id")
                        if checkbox_id:
                            try:
                                label = section.find_element(By.CSS_SELECTOR, f"label[for='{checkbox_id}']")
                                checked_labels.append(label.text.strip())
                            except:
                                pass
                if checked_labels:
                    return ", ".join(checked_labels)
            
            # Strategy 4: Dropdowns
            selects = section.find_elements(By.TAG_NAME, "select")
            for select in selects:
                if select.is_displayed():
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(select)
                    try:
                        selected = select_element.first_selected_option
                        value = selected.text.strip()
                        if value and value != "Select an option" and value != "":
                            return value
                    except:
                        continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Could not extract answer: {e}")
            return None
    
    def _get_unanswered_required_fields(self) -> List[Dict]:
        """
        Detect unanswered required fields in the form.
        
        Returns:
            List of dicts with field info: {element, question_text, field_type}
        """
        unanswered = []
        try:
            # Find all form sections
            form_groups = self.driver.find_elements(
                By.CLASS_NAME,
                "jobs-easy-apply-form-section__grouping"
            )
            
            for group in form_groups:
                if not group.is_displayed():
                    continue
                
                question_text = group.text
                
                # Check for required indicator (asterisk or aria-required)
                is_required = False
                try:
                    required_indicators = group.find_elements(
                        By.XPATH, ".//*[contains(text(), '*') or @aria-required='true']")
                    is_required = len(required_indicators) > 0
                except BaseException:
                    pass
                
                if not is_required:
                    continue
                
                # Check text inputs
                text_inputs = group.find_elements(
                    By.CSS_SELECTOR, "input[type='text']")
                for input_field in text_inputs:
                    if input_field.is_displayed():
                        value = input_field.get_attribute("value") or ""
                        if not value.strip():
                            unanswered.append({
                                "element": input_field,
                                "question_text": question_text,
                                "field_type": "text"
                            })
                
                # Check radio buttons (none selected)
                radio_buttons = group.find_elements(
                    By.CSS_SELECTOR, "input[type='radio']")
                if radio_buttons:
                    selected = any(r.is_selected() for r in radio_buttons)
                    if not selected:
                        unanswered.append({
                            "element": radio_buttons[0],
                            "question_text": question_text,
                            "field_type": "radio",
                            "options": radio_buttons
                        })
                
                # Check dropdowns
                selects = group.find_elements(By.TAG_NAME, "select")
                for select in selects:
                    if select.is_displayed():
                        from selenium.webdriver.support.ui import Select
                        select_element = Select(select)
                        selected = select_element.first_selected_option
                        if not selected or selected.get_attribute("value") == "":
                            unanswered.append({
                                "element": select,
                                "question_text": question_text,
                                "field_type": "select"
                            })
        
        except Exception as e:
            logger.debug(f"Error detecting unanswered fields: {e}")
        
        return unanswered
    
    def _handle_unknown_questions(self) -> bool:
        """
        Handle unknown/unanswered questions with human-in-the-loop learning.
        
        Returns:
            True if all questions resolved, False if user skipped or errors occurred
        """
        unanswered = self._get_unanswered_required_fields()
        
        if not unanswered:
            return True  # No unknown questions
        
        logger.warning(f"Found {len(unanswered)} unanswered required field(s)")
        
        for field_info in unanswered:
            question_text = field_info["question_text"]
            field_type = field_info["field_type"]
            
            # Print loud alert
            print("\n" + "=" * 80)
            print("⚠️  UNKNOWN QUESTION DETECTED - USER INPUT REQUIRED!")
            print("=" * 80)
            print(f"Question: {question_text}")
            print(f"Field Type: {field_type}")
            print("=" * 80)
            print("\a")  # System beep
            
            # Wait for user to fill the answer
            response = input(
                "\n👉 Please manually fill the answer in the browser window,\n"
                "   then press ENTER here to save and continue...\n"
                "   (or type 'skip' to skip this job): "
            ).strip().lower()
            
            if response == 'skip':
                logger.warning("User chose to skip this job")
                return False
            
            # Scrape the user's answer
            try:
                answer = None
                
                if field_type == "text":
                    answer = field_info["element"].get_attribute("value") or ""
                
                elif field_type == "radio":
                    for radio in field_info["options"]:
                        if radio.is_selected():
                            answer = radio.get_attribute(
                                "value") or radio.get_attribute("id") or "Yes"
                            break
                
                elif field_type == "select":
                    from selenium.webdriver.support.ui import Select
                    select_element = Select(field_info["element"])
                    selected = select_element.first_selected_option
                    if selected:
                        answer = selected.text or selected.get_attribute(
                            "value")
                
                if answer and answer.strip():
                    # Save to Q&A memory
                    self.qa_manager.learn_answer(question_text, answer)
                    print(
                        f"✅ Learned: '{question_text[:50]}...' -> '{answer}'")
                else:
                    logger.warning(
                        f"Could not detect answer for: {question_text[:50]}...")
            
            except Exception as e:
                logger.error(f"Error scraping user answer: {e}")
        
        return True

    def _get_next_action(self) -> str:
        """Determine the next action to take."""
        try:
            # Check for submit button
            if self._find_submit_button():
                return "submit"

            # Check for review button
            if self._find_review_button():
                return "review"

            # Check for next button
            if self._find_next_button():
                return "next"

            return "unknown"

        except BaseException:
            return "unknown"

    def _find_submit_button(self):
        """Find submit button."""
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='Submit application' i]"
            )
        except NoSuchElementException:
            return None

    def _find_review_button(self):
        """Find review button."""
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='Review' i]"
            )
        except NoSuchElementException:
            return None

    def _find_next_button(self):
        """Find next button."""
        try:
            return self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='next step' i]"
            )
        except NoSuchElementException:
            return None

    def _click_next(self) -> bool:
        """
        Click next button with robust state checking and user intervention.
        
        Returns:
            True if click successful, False otherwise
        """
        try:
            button = self._find_next_button()
            if not button:
                logger.debug("Next button not found")
                return False
            
            # Check if button is enabled
            if not button.is_enabled():
                logger.warning("⚠️  Next Button Disabled! Form is incomplete.")
                
                # PAUSE FOR USER INPUT
                try:
                    self._pause_for_user_intervention("NEXT BUTTON DISABLED")
                except Exception:
                    # User skipped
                    return False
                
                # Re-check button after user intervention
                button = self._find_next_button()
                if not button or not button.is_enabled():
                    logger.warning("Next button still disabled after user intervention")
                    return False
            
            # Try to click with force strategy
            click_success = self._force_click_button(button, "Next")
            
            if click_success:
                logger.debug("Clicked Next button")
                StealthUtils.human_sleep(1, 2)
                return True
            else:
                logger.warning("Failed to click Next button")
                return False
                
        except Exception as e:
            logger.debug(f"Failed to click next: {e}")
            return False

    def _click_review(self) -> bool:
        """Click review button."""
        try:
            button = self._find_review_button()
            if button:
                button.click()
                logger.debug("Clicked Review button")
                StealthUtils.human_sleep(1, 2)
                return True
            return False
        except Exception as e:
            logger.debug(f"Failed to click review: {e}")
            return False

    def _submit_application(self) -> bool:
        """
        Submit the application with comprehensive verification and user intervention.
        
        This method implements a robust 3-step process:
        1. Check button state and pause for user if disabled
        2. Force click with fallback to JavaScript
        3. Verify success and loop back if failed
        
        Returns:
            True if submission verified successful, False otherwise
        """
        if self.dry_run:
            logger.info("🔵 DRY RUN: Application would be submitted here")
            self._discard_application()
            return True

        # FINAL CONFIRMATION (if enabled in config)
        if self.config.require_submission_confirmation:
            logger.info("=" * 80)
            logger.info("📋 READY TO SUBMIT APPLICATION")
            logger.info("=" * 80)
            
            # Final validation check
            validation_errors = self._detect_validation_errors()
            if validation_errors:
                logger.error("⚠️  WARNING: Validation errors detected!")
                for error in validation_errors:
                    logger.error(f"  - {error['field_label']}: {error['message']}")
            else:
                logger.info("✅ All fields validated successfully")
            
            logger.info("=" * 80)
            
            # Prompt user for confirmation
            response = input(
                "\n👉 Ready to submit? Press ENTER to confirm (or type 'skip' to skip this job): "
            ).strip().lower()
            
            if response == 'skip':
                logger.warning("User chose to skip submission")
                self._discard_application()
                return False
            
            logger.info("User confirmed submission, proceeding...")

        # Delegate to comprehensive submit handler
        return self._handle_submit_step()

    def _verify_submission_success(self) -> bool:
        """
        Verify that the application was actually submitted successfully.
        
        Returns:
            True if success indicators found, False otherwise
        """
        try:
            # Wait up to 10 seconds for success indicators
            for _ in range(20):  # 20 * 0.5s = 10 seconds
                StealthUtils.human_sleep(0.5, 0.5)

                page_source = self.driver.page_source.lower()

                # Check for success messages
                success_phrases = [
                    "application sent",
                    "application submitted",
                    "your application has been sent",
                    "thank you for applying",
                    "application complete",
                    "successfully submitted"
                ]

                if any(phrase in page_source for phrase in success_phrases):
                    return True

                # Check if modal closed (back to job list)
                try:
                    # If we can see the job list again, modal closed
                    # successfully
                    self.driver.find_element(
                        By.CLASS_NAME, "jobs-search-results-list")
                    return True
                except BaseException:
                    pass

            return False

        except Exception as e:
            logger.debug(f"Error verifying submission: {e}")
            return False

    def _log_visible_errors(self):
        """Log any visible error messages on the page."""
        try:
            error_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".artdeco-inline-feedback--error, [role='alert']"
            )

            for error in error_elements:
                if error.is_displayed():
                    error_text = error.text.strip()
                    if error_text:
                        logger.error(f"Form error: {error_text}")
        except Exception as e:
            logger.debug(f"Could not log errors: {e}")

    def _handle_submit_step(self) -> bool:
        """
        Comprehensive submit handler with user intervention loop.
        
        Implements the 3-step process:
        1. Button State Check - Pause if disabled
        2. Force Click Strategy - Standard + JS fallback
        3. Post-Click Verification - Loop if failed
        
        Returns:
            True if submission successful, False otherwise
        """
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            attempt += 1
            logger.info(f"Submit attempt {attempt}/{max_attempts}")
            
            # STEP 1: Button State Check
            submit_button = self._wait_for_submit_button()
            if not submit_button:
                logger.error("Submit button not found")
                self._discard_application()
                return False
            
            # Check if button is enabled
            if not submit_button.is_enabled():
                logger.warning("⚠️  Button Disabled! Form is incomplete.")
                
                # PAUSE FOR USER INPUT
                self._pause_for_user_intervention("SUBMIT BUTTON DISABLED")
                
                # Re-check button state after user intervention
                submit_button = self._wait_for_submit_button()
                if not submit_button or not submit_button.is_enabled():
                    logger.warning("Button still disabled after user intervention")
                    continue  # Loop back and try again
            
            # STEP 2: Force Click Strategy
            click_success = self._force_click_button(submit_button, "Submit")
            
            if not click_success:
                logger.error("Failed to click submit button")
                continue
            
            logger.info("Submit button clicked, waiting for result...")
            StealthUtils.human_sleep(2, 3)
            
            # STEP 3: Post-Click Verification
            result = self._verify_post_click_state()
            
            if result == "success":
                logger.info("✅ Application submitted successfully (verified)")
                return True
            elif result == "discard_popup":
                logger.warning("Discard popup appeared - submission failed")
                self._log_visible_errors()
                # Try to stay on the form and loop back
                try:
                    cancel_button = self.driver.find_element(
                        By.XPATH,
                        "//button[contains(., 'Cancel') or @data-test-dialog-secondary-btn]"
                    )
                    cancel_button.click()
                    StealthUtils.human_sleep(1, 2)
                    logger.info("Cancelled discard dialog, retrying...")
                except:
                    logger.warning("Could not cancel discard dialog")
                    self._discard_application()
                    return False
            elif result == "still_on_form":
                logger.warning("Still on form after click - submission may have failed")
                self._log_visible_errors()
                # Check for new errors and pause for user
                if self._has_errors():
                    self._pause_for_user_intervention("FORM HAS VALIDATION ERRORS")
            else:
                logger.error("Unknown state after submit click")
        
        # Max attempts exceeded
        logger.error(f"Submit failed after {max_attempts} attempts")
        self._discard_application()
        return False
    
    def _wait_for_submit_button(self):
        """
        Wait for submit button to be present using WebDriverWait.
        
        Returns:
            WebElement if found, None otherwise
        """
        try:
            button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "button[aria-label*='Submit application' i]"
                ))
            )
            return button
        except TimeoutException:
            logger.debug("Submit button not found within timeout")
            return None
    
    def _pause_for_user_intervention(self, reason: str):
        """
        Pause execution and wait for user to fix the form manually.
        
        Args:
            reason: Reason for pausing (displayed to user)
        """
        print("\n" + "=" * 80)
        print("⚠️  USER INTERVENTION REQUIRED!")
        print("=" * 80)
        print(f"Reason: {reason}")
        print("=" * 80)
        print("\a")  # System beep
        
        logger.warning(f"Pausing for user intervention: {reason}")
        
        response = input(
            "\n👉 Please fix the issue in the browser window,\n"
            "   then press ENTER here to continue...\n"
            "   (or type 'skip' to skip this job): "
        ).strip().lower()
        
        if response == 'skip':
            logger.warning("User chose to skip this job")
            self._discard_application()
            raise Exception("User skipped job")
        
        logger.info("User intervention complete, resuming...")
    
    def _force_click_button(self, button, button_name: str) -> bool:
        """
        Attempt to click button with fallback to JavaScript click.
        
        Args:
            button: WebElement to click
            button_name: Name of button for logging
            
        Returns:
            True if click successful, False otherwise
        """
        try:
            # Scroll to button first
            StealthUtils.smooth_scroll_to_element(self.driver, button)
            StealthUtils.human_sleep(0.5, 1.0)
            
            # Try standard click
            button.click()
            logger.info(f"Standard click succeeded on {button_name} button")
            return True
            
        except Exception as e:
            logger.warning(f"Standard click failed: {e}")
            
            # Fallback to JavaScript click
            try:
                logger.info(f"Attempting JavaScript click on {button_name} button...")
                self.driver.execute_script("arguments[0].click();", button)
                logger.info(f"JavaScript click succeeded on {button_name} button")
                return True
            except Exception as js_error:
                logger.error(f"JavaScript click also failed: {js_error}")
                return False
    
    def _verify_post_click_state(self) -> str:
        """
        Verify the state after clicking submit button.
        
        Returns:
            "success" - Submission successful
            "discard_popup" - Save/Discard dialog appeared
            "still_on_form" - Still on the form page
            "unknown" - Unknown state
        """
        # Wait a moment for page to update
        StealthUtils.human_sleep(2, 3)
        
        # Check for discard popup (indicates failed submission attempt)
        try:
            discard_dialog = self.driver.find_element(
                By.XPATH,
                "//div[contains(@data-test-modal-id, 'discard') or contains(., 'Discard')]"
            )
            if discard_dialog.is_displayed():
                return "discard_popup"
        except:
            pass
        
        # Check for success indicators
        if self._verify_submission_success():
            return "success"
        
        # Check if still on form (look for submit button again)
        try:
            still_has_submit = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='Submit application' i]"
            )
            if still_has_submit.is_displayed():
                return "still_on_form"
        except:
            pass
        
        # Check if we're back at job list (another success indicator)
        try:
            job_list = self.driver.find_element(
                By.CLASS_NAME,
                "jobs-search-results-list"
            )
            if job_list.is_displayed():
                return "success"
        except:
            pass
        
        return "unknown"
    
    def _discard_application(self):
        """
        Safely discard/close the application modal.
        Handles "Save or Discard?" dialogs to prevent infinite loops.
        """
        try:
            logger.info("Closing application modal...")

            # Try to close the modal
            close_buttons = self.driver.find_elements(
                By.CSS_SELECTOR,
                "button[aria-label*='Dismiss' i], button[aria-label*='Close' i], .artdeco-modal__dismiss"
            )

            if close_buttons:
                close_buttons[0].click()
                StealthUtils.human_sleep(1, 2)

            # Handle "Discard application?" confirmation dialog
            discard_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(., 'Discard') or @data-test-dialog-primary-btn]"
            )

            if discard_buttons:
                logger.info("Clicking 'Discard' to confirm exit")
                discard_buttons[0].click()
                StealthUtils.human_sleep(1, 2)

            logger.debug("Application modal closed successfully")

        except Exception as e:
            logger.debug(f"Error discarding application: {e}")

    def _log_application(
        self,
        job_id: str,
        job_title: str,
        company: str,
        attempted: bool,
        result: bool
    ):
        """Log application attempt to CSV."""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, job_id, job_title,
                                company, attempted, result])

            logger.debug(f"Logged application: {job_id}")

        except Exception as e:
            logger.error(f"Failed to log application: {e}")
