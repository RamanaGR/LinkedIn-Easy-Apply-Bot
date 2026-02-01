"""
Q&A Memory Manager - Self-Learning Question Answering System

This module handles persistent storage and retrieval of question-answer pairs
learned from user interactions during job applications.
"""

import csv
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.logger import get_logger

# Initialize logger first
logger = get_logger()

# Fuzzy string matching for intelligent question retrieval
try:
    from thefuzz import fuzz, process
    FUZZY_MATCHING_AVAILABLE = True
except ImportError:
    FUZZY_MATCHING_AVAILABLE = False
    logger.warning("⚠️ thefuzz not installed - using exact matching only")
    logger.warning("Install with: pip install thefuzz python-Levenshtein")


class QAMemoryManager:
    """Manages the persistent Q&A knowledge base."""
    
    def __init__(self, memory_file: str = "qa_memory.csv"):
        """
        Initialize the Q&A memory manager.
        
        Args:
            memory_file: Path to the CSV file storing Q&A pairs
        """
        self.memory_file = Path(memory_file)
        self.memory: Dict[str, str] = {}
        
        # Ensure file exists
        self._ensure_memory_file()
        
        # Load existing knowledge
        self._load_memory()
    
    def _ensure_memory_file(self):
        """Create the memory file if it doesn't exist."""
        if not self.memory_file.exists():
            self.memory_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.memory_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['question_text', 'answer_text'])
            logger.info(f"Created Q&A memory file: {self.memory_file}")
    
    def _load_memory(self):
        """Load all Q&A pairs from the CSV file into memory."""
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    question = self._normalize_text(row['question_text'])
                    answer = row['answer_text'].strip()
                    self.memory[question] = answer
            
            logger.info(f"Loaded {len(self.memory)} Q&A pairs from memory")
        
        except Exception as e:
            logger.error(f"Failed to load Q&A memory: {e}")
            self.memory = {}
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize question text for consistent matching.
        
        Args:
            text: Raw question text
            
        Returns:
            Normalized text (lowercase, stripped, single spaces)
        """
        # Convert to lowercase
        text = text.lower()
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Replace multiple spaces with single space
        text = ' '.join(text.split())
        
        # Remove common punctuation that doesn't affect meaning
        text = text.replace('?', '').replace(':', '').replace('*', '')
        
        return text
    
    def lookup_answer(self, question: str) -> Optional[str]:
        """
        Look up an answer for a given question using fuzzy matching.
        
        Strategy:
        1. Try exact match first (fastest)
        2. If not found, use fuzzy matching with 90% threshold
        3. Return best match if threshold met
        
        Args:
            question: Question text
            
        Returns:
            Answer if found, None otherwise
        """
        normalized_question = self._normalize_text(question)
        
        # Step 1: Try exact match first (O(1) lookup)
        answer = self.memory.get(normalized_question)
        if answer:
            logger.debug(f"✅ [EXACT MATCH] Found: '{question[:50]}...'")
            return answer
        
        # Step 2: If no exact match and fuzzy matching is available, try fuzzy match
        if FUZZY_MATCHING_AVAILABLE and len(self.memory) > 0:
            try:
                # Find best match using fuzzy string matching
                best_match = process.extractOne(
                    normalized_question,
                    self.memory.keys(),
                    scorer=fuzz.ratio
                )
                
                if best_match:
                    matched_question, score = best_match[0], best_match[1]
                    
                    # Use 90% threshold for high confidence matching
                    if score >= 90:
                        answer = self.memory[matched_question]
                        logger.info(
                            f"✅ [FUZZY MATCH {score}%] '{question[:40]}...' "
                            f"matched '{matched_question[:40]}...'"
                        )
                        return answer
                    else:
                        logger.debug(
                            f"❌ Best match only {score}% similar (threshold: 90%)"
                        )
            except Exception as e:
                logger.error(f"Fuzzy matching error: {e}")
        
        # No match found
        logger.debug(f"❌ No match found for: '{question[:50]}...'")
        return None
    
    def learn_answer(self, question: str, answer: str) -> bool:
        """
        Learn a new Q&A pair and save it immediately.
        Prevents duplicates by rewriting the entire CSV.
        
        Args:
            question: Question text
            answer: User-provided answer
            
        Returns:
            True if successfully saved, False otherwise
        """
        try:
            normalized_question = self._normalize_text(question)
            
            # Check if this is an update or new entry
            is_update = normalized_question in self.memory
            
            # Update in-memory cache (this handles both new and updates)
            self.memory[normalized_question] = answer
            
            # CRITICAL: Rewrite ENTIRE CSV to prevent duplicates
            # This ensures the CSV matches the in-memory dictionary exactly
            with open(self.memory_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow(['question_text', 'answer_text'])
                
                # Write all Q&A pairs from memory
                for q, a in self.memory.items():
                    writer.writerow([q, a])
                
                f.flush()  # Force write to disk
            
            if is_update:
                logger.info(f"🔄 Updated: '{question[:50]}...' -> '{answer}'")
            else:
                logger.info(f"✅ Learned: '{question[:50]}...' -> '{answer}'")
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to save Q&A pair: {e}")
            return False
    
    def prompt_user_for_answer(self, question: str) -> Tuple[Optional[str], bool]:
        """
        Prompt user for an answer to an unknown question.
        
        Args:
            question: Question text that needs an answer
            
        Returns:
            Tuple of (answer, should_skip)
            - (answer, False) if user provided an answer
            - (None, True) if user wants to skip
        """
        # Print loud alert
        print("\n" + "=" * 80)
        print("[MISSING ANSWER] Q&A Memory Gap Detected!")
        print("=" * 80)
        print(f"Question: \"{question}\"")
        print("=" * 80)
        print("\a")  # System beep
        
        logger.warning(f"Missing answer for: {question[:50]}...")
        
        # Prompt user
        response = input(
            "\n👉 Enter answer for this question (or type 'SKIP' to ignore): "
        ).strip()
        
        if response.upper() == 'SKIP':
            logger.info("User chose to skip this question")
            return None, True
        
        if not response:
            logger.warning("Empty answer provided, treating as skip")
            return None, True
        
        return response, False
    
    def get_memory_stats(self) -> Dict[str, int]:
        """
        Get statistics about the Q&A memory.
        
        Returns:
            Dictionary with stats
        """
        return {
            "total_pairs": len(self.memory),
            "file_size_bytes": self.memory_file.stat().st_size if self.memory_file.exists() else 0
        }
    
    def export_memory(self, output_file: str):
        """
        Export the current memory to a different file.
        
        Args:
            output_file: Path to export file
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['question_text', 'answer_text'])
                
                for question, answer in self.memory.items():
                    writer.writerow([question, answer])
            
            logger.info(f"Exported {len(self.memory)} Q&A pairs to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to export memory: {e}")
    
    def clear_memory(self):
        """Clear all Q&A pairs from memory (use with caution!)."""
        self.memory.clear()
        logger.warning("Cleared all Q&A pairs from memory (not from file)")
    
    def reload_memory(self):
        """Reload Q&A pairs from file."""
        self.memory.clear()
        self._load_memory()
        logger.info("Reloaded Q&A memory from file")
    
    def deduplicate_memory(self) -> int:
        """
        Remove duplicate entries from the CSV file.
        
        The in-memory dictionary naturally handles duplicates (dict keys are unique),
        so we just need to rewrite the CSV from memory.
        
        Returns:
            Number of unique entries after deduplication
        """
        try:
            # Count original entries
            original_count = 0
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    original_count = sum(1 for _ in f) - 1  # Subtract header
            except:
                pass
            
            # Reload memory (this automatically deduplicates via dict)
            self.reload_memory()
            
            # Rewrite entire CSV from deduplicated memory
            with open(self.memory_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['question_text', 'answer_text'])
                
                for question, answer in self.memory.items():
                    writer.writerow([question, answer])
            
            duplicates_removed = original_count - len(self.memory)
            
            if duplicates_removed > 0:
                logger.info(
                    f"🧹 Deduplication complete: "
                    f"{original_count} entries → {len(self.memory)} unique "
                    f"(removed {duplicates_removed} duplicates)"
                )
            else:
                logger.info(f"✅ No duplicates found ({len(self.memory)} unique entries)")
            
            return len(self.memory)
        
        except Exception as e:
            logger.error(f"Failed to deduplicate memory: {e}")
            return len(self.memory)
