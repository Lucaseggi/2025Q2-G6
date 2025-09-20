"""Response verification for LLM output quality control"""

import json
import logging
import difflib
import re
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ResponseVerifier:
    """Handles LLM response verification and quality control"""

    def __init__(self, diff_threshold: float = 0.15):
        self.diff_threshold = diff_threshold

    def calculate_text_similarity(self, original: str, structured: str) -> float:
        """Calculate content-focused similarity between original and structured text"""
        # Clean the JSON response
        clean_json = structured.strip()
        if clean_json.startswith('```json'):
            clean_json = clean_json[7:]
        if clean_json.endswith('```'):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        try:
            data = json.loads(clean_json)
            extracted_text = self._extract_structured_text(data)
        except Exception as e:
            logger.warning(f"Failed to parse JSON for similarity: {e}")
            return 0.0

        # Use content-focused similarity instead of character-level
        similarity = self._calculate_content_similarity(original, extracted_text)

        # Debug logging
        original_clean = self._clean_text_for_comparison(original)
        extracted_clean = self._clean_text_for_comparison(extracted_text)
        logger.info(
            f"DEBUG: Original clean ({len(original_clean)} chars): '{original_clean[:300]}...'"
        )
        logger.info(
            f"DEBUG: Extracted clean ({len(extracted_clean)} chars): '{extracted_clean[:300]}...'"
        )
        logger.info(f"DEBUG: Content similarity score: {similarity:.4f}")

        return similarity

    def _calculate_content_similarity(self, original: str, extracted: str) -> float:
        """Calculate content-focused similarity using word-level analysis"""
        # Normalize both texts
        original_words = self._extract_content_words(original)
        extracted_words = self._extract_content_words(extracted)

        # Calculate word-level similarity
        matcher = difflib.SequenceMatcher(None, original_words, extracted_words)
        word_similarity = matcher.ratio()

        # Calculate word set similarity (Jaccard similarity)
        original_set = set(original_words)
        extracted_set = set(extracted_words)
        if not original_set and not extracted_set:
            set_similarity = 1.0
        elif not original_set or not extracted_set:
            set_similarity = 0.0
        else:
            intersection = original_set.intersection(extracted_set)
            union = original_set.union(extracted_set)
            set_similarity = len(intersection) / len(union)

        # Detect potential hallucination by checking for added content
        original_set = set(original_words)
        extracted_set = set(extracted_words)
        added_words = extracted_set - original_set

        # Calculate hallucination penalty based on new words
        hallucination_penalty = 1.0
        if len(added_words) > 0:
            # Penalty based on ratio of new words to original content
            added_ratio = len(added_words) / max(len(original_words), 1)
            if added_ratio > 0.05:  # More than 5% new words
                # Strong penalty for potential hallucination
                hallucination_penalty = max(0.4, 1.0 - (added_ratio * 3.0))
                logger.info(
                    f"DEBUG: Hallucination penalty - added words: {len(added_words)}, ratio: {added_ratio:.3f}, penalty: {hallucination_penalty:.3f}"
                )

        # Length penalty for significantly shorter content (truncation detection)
        length_ratio = len(extracted_words) / max(len(original_words), 1)
        length_penalty = 1.0
        if length_ratio < 0.8:  # More than 20% shorter
            missing_ratio = 0.8 - length_ratio
            length_penalty = max(0.3, 1.0 - (missing_ratio * 2.0))
            logger.info(
                f"DEBUG: Truncation penalty - ratio: {length_ratio:.3f}, penalty: {length_penalty:.3f}"
            )

        # Weighted combination (favor word order but also consider content coverage)
        combined_similarity = (word_similarity * 0.7) + (set_similarity * 0.3)

        # Apply both penalties
        final_similarity = combined_similarity * hallucination_penalty * length_penalty

        logger.info(
            f"DEBUG: Word similarity: {word_similarity:.4f}, Set similarity: {set_similarity:.4f}"
        )
        logger.info(
            f"DEBUG: Length ratio: {length_ratio:.3f}, Final similarity: {final_similarity:.4f}"
        )

        return final_similarity

    def _extract_content_words(self, text: str) -> list:
        """Extract meaningful content words, filtering out structural elements"""
        # Basic text cleaning
        text = text.lower()
        text = re.sub(r'\s+', ' ', text)

        # Split into words
        words = text.split()

        # Filter out article headers and structural words
        content_words = []
        skip_patterns = [
            r'^artículo$',
            r'^articulo$',
            r'^art\.$',  # Article headers
            r'^\d+[°\.]*$',  # Standalone numbers
            r'^[-–—]+$',  # Dashes
            r'^\.$',
            r'^,$',
            r'^;$',
            r'^:$',  # Standalone punctuation
        ]

        for word in words:
            # Skip if word matches any skip pattern
            skip = False
            for pattern in skip_patterns:
                if re.match(pattern, word):
                    skip = True
                    break

            if not skip and len(word) > 1:  # Skip single characters
                # Clean the word of trailing punctuation but keep meaningful parts
                cleaned_word = re.sub(r'[^\w]$', '', word)
                if cleaned_word:
                    content_words.append(cleaned_word)

        return content_words

    # This relies heavily on the prompt
    def _extract_structured_text(self, data: dict) -> str:
        """Extract only content text from JSON structure (excludes metadata like numbers)"""
        text_parts = []

        # Extract text from divisions structure
        divisions = data.get('divisions', [])
        if isinstance(divisions, list):
            for division in divisions:
                if isinstance(division, dict):
                    self._extract_text_from_division(division, text_parts)

        return ' '.join(text_parts)

    def _extract_text_from_division(self, division: dict, text_parts: list):
        """Recursively extract text from a division and its nested content"""
        # Extract division body text
        body = division.get('body', '')
        if body and body.strip():
            text_parts.append(body.strip())

        # Extract articles text (sorted by order to preserve sequence)
        articles = division.get('articles', [])
        if isinstance(articles, list):
            # Sort by order field if available, otherwise use original order
            sorted_articles = sorted(articles, key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
            for article in sorted_articles:
                if isinstance(article, dict):
                    self._extract_text_from_article(article, text_parts)

        # Extract nested divisions recursively (sorted by order)
        nested_divisions = division.get('divisions', [])
        if isinstance(nested_divisions, list):
            # Sort by order field if available, otherwise use original order
            sorted_divisions = sorted(nested_divisions, key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
            for nested_division in sorted_divisions:
                if isinstance(nested_division, dict):
                    self._extract_text_from_division(nested_division, text_parts)

    def _extract_text_from_article(self, article: dict, text_parts: list):
        """Recursively extract text from an article and its sub-articles"""
        # Extract article body text
        body = article.get('body', '')
        if body and body.strip():
            text_parts.append(body.strip())

        # Extract nested articles recursively (sorted by order)
        nested_articles = article.get('articles', [])
        if isinstance(nested_articles, list):
            # Sort by order field if available, otherwise use original order
            sorted_nested_articles = sorted(nested_articles, key=lambda x: x.get('order', 0) if isinstance(x, dict) else 0)
            for nested_article in sorted_nested_articles:
                if isinstance(nested_article, dict):
                    self._extract_text_from_article(nested_article, text_parts)

    def _clean_text_for_comparison(self, text: str) -> str:
        """Clean text for similarity comparison"""
        # Convert to lowercase first
        text = text.lower()

        # Remove common prefixes/headers
        text = re.sub(r'^texto norma:\s*', '', text)
        text = re.sub(r'^texto norma actualizado:\s*', '', text)

        # Normalize whitespace and line breaks
        text = re.sub(r'\s+', ' ', text)

        # Remove common separators and formatting
        text = re.sub(r'-{2,}', '', text)  # Remove ---- separators
        text = re.sub(r'[°\.]\s*', ' ', text)  # N° -> N

        return text.strip()


    def generate_content_diff(self, original_text: str, structured_text: str) -> str:
        """Generate a readable diff between original and structured text"""
        # Extract text from structured JSON using the proper extraction method
        try:
            clean_json = structured_text.strip()
            if clean_json.startswith('```json'):
                clean_json = clean_json[7:]
            if clean_json.endswith('```'):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()

            structured_data = json.loads(clean_json)
            extracted_text = self._extract_structured_text(structured_data)
        except Exception as e:
            logger.warning(f"Failed to extract text from JSON for diff: {e}")
            extracted_text = structured_text

        # Clean both texts for comparison
        original_clean = self._clean_text_for_comparison(original_text)
        extracted_clean = self._clean_text_for_comparison(extracted_text)

        # Generate unified diff
        original_lines = original_clean.splitlines()
        extracted_lines = extracted_clean.splitlines()

        diff_lines = list(
            difflib.unified_diff(
                original_lines,
                extracted_lines,
                fromfile='original',
                tofile='llm_extracted',
                lineterm='',
            )
        )

        return '\n'.join(diff_lines)

    def validate_json_structure(
        self, structured_data: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """Validate JSON structure against expected schema"""
        try:
            # Required top-level field
            if "divisions" not in structured_data:
                return False, "Missing required field: divisions"

            divisions = structured_data.get("divisions", [])
            if not isinstance(divisions, list):
                return False, "Field 'divisions' must be a list"

            # Inject order fields to preserve document sequence
            self._inject_order_fields(structured_data)

            # Validate each division
            for i, division in enumerate(divisions):
                is_valid, error_msg = self._validate_division(division, f"Division {i}")
                if not is_valid:
                    return False, error_msg

            return True, "JSON structure validation passed"

        except Exception as e:
            return False, f"JSON validation error: {str(e)}"

    def _validate_division(self, division: dict, context: str) -> Tuple[bool, str]:
        """Validate a single division structure"""
        if not isinstance(division, dict):
            return False, f"{context} is not a dictionary"

        # Required fields for division
        required_fields = ["name", "ordinal", "title", "body", "articles", "divisions"]
        for field in required_fields:
            if field not in division:
                return False, f"{context} missing required field: {field}"

        # Validate field types
        string_fields = ["name", "ordinal", "title", "body"]
        for field in string_fields:
            value = division.get(field)
            if value is not None and not isinstance(value, str):
                return False, f"{context} field '{field}' must be a string, got {type(value)}"

        # Validate articles array
        articles = division.get("articles", [])
        if not isinstance(articles, list):
            return False, f"{context} field 'articles' must be a list"

        for j, article in enumerate(articles):
            is_valid, error_msg = self._validate_article(article, f"{context} article {j}")
            if not is_valid:
                return False, error_msg

        # Validate nested divisions array
        nested_divisions = division.get("divisions", [])
        if not isinstance(nested_divisions, list):
            return False, f"{context} field 'divisions' must be a list"

        for k, nested_division in enumerate(nested_divisions):
            is_valid, error_msg = self._validate_division(nested_division, f"{context} nested division {k}")
            if not is_valid:
                return False, error_msg

        return True, ""

    def _inject_order_fields(self, structured_data: dict):
        """Inject order fields to preserve document sequence"""
        divisions = structured_data.get('divisions', [])
        for div_index, division in enumerate(divisions):
            division['order'] = div_index + 1
            self._inject_division_order(division)

    def _inject_division_order(self, division: dict):
        """Recursively inject order fields within a division"""
        # Add order to articles within this division
        articles = division.get('articles', [])
        for art_index, article in enumerate(articles):
            article['order'] = art_index + 1
            self._inject_article_order(article)

        # Recursively handle nested divisions
        nested_divisions = division.get('divisions', [])
        for nested_index, nested_div in enumerate(nested_divisions):
            nested_div['order'] = nested_index + 1
            self._inject_division_order(nested_div)

    def _inject_article_order(self, article: dict):
        """Recursively inject order fields within nested articles"""
        nested_articles = article.get('articles', [])
        for nested_index, nested_article in enumerate(nested_articles):
            nested_article['order'] = nested_index + 1
            self._inject_article_order(nested_article)

    def _validate_article(self, article: dict, context: str) -> Tuple[bool, str]:
        """Validate a single article structure"""
        if not isinstance(article, dict):
            return False, f"{context} is not a dictionary"

        # Required fields for article
        required_fields = ["ordinal", "body", "articles"]
        for field in required_fields:
            if field not in article:
                return False, f"{context} missing required field: {field}"

        # Validate field types
        string_fields = ["ordinal", "body"]
        for field in string_fields:
            value = article.get(field)
            if value is not None and not isinstance(value, str):
                return False, f"{context} field '{field}' must be a string, got {type(value)}"

        # Validate nested articles array
        nested_articles = article.get("articles", [])
        if not isinstance(nested_articles, list):
            return False, f"{context} field 'articles' must be a list"

        for j, nested_article in enumerate(nested_articles):
            is_valid, error_msg = self._validate_article(nested_article, f"{context} nested article {j}")
            if not is_valid:
                return False, error_msg

        return True, ""
