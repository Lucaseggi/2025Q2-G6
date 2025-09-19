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

        # 1. Preamble - initial section content only
        preamble = data.get('preamble', '')
        if preamble and preamble.strip():
            text_parts.append(preamble.strip())

        # 2. Articles - only body content, skip numbers
        articles = data.get('articles', [])
        if isinstance(articles, list):
            for article in articles:
                if isinstance(article, dict):
                    article_text = article.get('body', '')
                    if article_text and article_text.strip():
                        text_parts.append(article_text.strip())

        # 3. Postamble - text after articles content only
        postamble = data.get('postamble', '')
        if postamble and postamble.strip():
            text_parts.append(postamble.strip())

        # 4. Short document - for documents without preamble/articles structure
        short_document = data.get('short_document', '')
        if short_document and short_document.strip():
            text_parts.append(short_document.strip())

        # 5. Firms - signatures and official names content only
        firms = data.get('firms', '')
        if firms and firms.strip():
            text_parts.append(firms.strip())

        # 6. Referenced articles text (only body content, skip metadata)
        references = data.get('references', [])
        if isinstance(references, list):
            for ref in references:
                if isinstance(ref, dict):
                    ref_articles = ref.get('articles', [])
                    if isinstance(ref_articles, list):
                        for ref_article in ref_articles:
                            if isinstance(ref_article, dict):
                                ref_article_text = ref_article.get('body', '')
                                if ref_article_text and ref_article_text.strip():
                                    text_parts.append(ref_article_text.strip())

        return ' '.join(text_parts)

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

    def should_escalate_model(self, original_text: str, structured_result: str) -> bool:
        """Determine if model should be escalated based on text similarity"""
        similarity = self.calculate_text_similarity(original_text, structured_result)

        # If similarity is too low, escalate
        threshold = self.diff_threshold
        should_escalate = similarity < (1.0 - threshold)

        if should_escalate:
            logger.info(
                f"Similarity {similarity:.3f} below threshold {1.0 - threshold:.3f}, escalating model"
            )

        return should_escalate

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
            # Required fields according to the prompt
            required_fields = [
                "preamble",
                "articles",
                "postamble",
                "short_document",
                "firms",
                "references",
            ]

            # Check all required fields exist
            for field in required_fields:
                if field not in structured_data:
                    return False, f"Missing required field: {field}"

            # Validate articles structure if present
            articles = structured_data.get("articles", [])
            if articles and isinstance(articles, list):
                for i, article in enumerate(articles):
                    if not isinstance(article, dict):
                        return False, f"Article {i} is not a dictionary"
                    if "number" not in article:
                        return False, f"Article {i} missing 'number' field"
                    if "body" not in article:
                        return False, f"Article {i} missing 'body' field"
                    # Validate number is integer or string convertible to int
                    try:
                        int(article["number"])
                    except (ValueError, TypeError):
                        return (
                            False,
                            f"Article {i} has invalid number format: {article.get('number')}",
                        )

            # Validate references structure if present
            references = structured_data.get("references", [])
            if references and isinstance(references, list):
                for i, ref in enumerate(references):
                    if not isinstance(ref, dict):
                        return False, f"Reference {i} is not a dictionary"
                    if "documentType" not in ref:
                        return False, f"Reference {i} missing 'documentType' field"
                    if "number" not in ref:
                        return False, f"Reference {i} missing 'number' field"
                    if "articles" not in ref:
                        return False, f"Reference {i} missing 'articles' field"

                    # Validate reference articles
                    ref_articles = ref.get("articles", [])
                    if ref_articles and isinstance(ref_articles, list):
                        for j, ref_article in enumerate(ref_articles):
                            if not isinstance(ref_article, dict):
                                return (
                                    False,
                                    f"Reference {i} article {j} is not a dictionary",
                                )
                            if "number" not in ref_article:
                                return (
                                    False,
                                    f"Reference {i} article {j} missing 'number' field",
                                )
                            if "body" not in ref_article:
                                return (
                                    False,
                                    f"Reference {i} article {j} missing 'body' field",
                                )

            # Check string fields are actually strings
            string_fields = ["preamble", "postamble", "short_document", "firms"]
            for field in string_fields:
                value = structured_data.get(field)
                if value is not None and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string, got {type(value)}"

            return True, "JSON structure validation passed"

        except Exception as e:
            return False, f"JSON validation error: {str(e)}"
