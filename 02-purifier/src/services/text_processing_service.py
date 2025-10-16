import re
import unicodedata
import logging
from bs4 import BeautifulSoup, NavigableString
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class TextProcessingService:
    """Service for text purification and processing"""

    UNICODE_SPACE_CHARS = (
        '\u00A0'  '\u1680'  '\u2000'  '\u2001'  '\u2002'  '\u2003'
        '\u2004'  '\u2005'  '\u2006'  '\u2007'  '\u2008'  '\u2009'
        '\u200A'  '\u202F'  '\u205F'  '\u3000'
    )

    RE_MULTI_WS = re.compile(r'\s+', flags=re.UNICODE)
    RE_MULTI_NEWLINES = re.compile(r'\n{3,}')

    def __init__(self):
        """Initialize text processing service"""
        self.logger = logging.getLogger(__name__)

    def normalize_ocr_artifacts(self, text: str) -> str:
        """Replace common OCR artifacts with proper counterparts"""
        if not text:
            return text

        replacements = {
            '—': '-', '–': '-', '―': '-', '−': '-',
            '"': '"', '"': '"', ''': "'", ''': "'", '´': "'", '`': "'",
            '…': '...',
            'º': '°',
            'À': 'Á', 'à': 'á', 'È': 'É', 'è': 'é',
            'Ì': 'Í', 'ì': 'í', 'Ò': 'Ó', 'ò': 'ó',
            'Ù': 'Ú', 'ù': 'ú',
        }

        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)

        return text

    def convert_html_to_structured_text(self, text: str) -> str:
        """Convert HTML to text while preserving structural information"""
        if not text:
            return text

        if '\u00C2\u00A0' in text:
            text = text.replace('\u00C2\u00A0', '\u00A0')

        soup = BeautifulSoup(text, "html.parser")

        BLOCK_TAGS = {
            'p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'article', 'section', 'header', 'footer', 'nav', 'aside',
            'blockquote', 'pre', 'hr', 'ul', 'ol', 'li', 'dl', 'dt', 'dd'
        }

        INLINE_TAGS = {
            'b', 'i', 'em', 'strong', 'span', 'a', 'u', 'sub', 'sup',
            'code', 'kbd', 'samp', 'var', 'small', 'big', 'tt'
        }

        def process_element(element):
            """Recursively process HTML elements"""
            if isinstance(element, NavigableString):
                return str(element)

            result = []
            tag_name = element.name.lower() if element.name else ''

            if tag_name in BLOCK_TAGS:
                result.append('\n')

            for child in element.children:
                child_text = process_element(child)
                if child_text:
                    result.append(child_text)

            if tag_name in BLOCK_TAGS:
                result.append('\n')
            elif tag_name in INLINE_TAGS:
                result.append(' ')

            return ''.join(result)

        structured_text = process_element(soup)
        structured_text = self.normalize_whitespace_preserve_structure(structured_text)
        structured_text = self.normalize_ocr_artifacts(structured_text)

        return structured_text

    def normalize_whitespace_preserve_structure(self, text: str) -> str:
        """Normalize whitespace while preserving line break structure"""
        if not text:
            return text

        trans = {ord(ch): ord(' ') for ch in self.UNICODE_SPACE_CHARS}
        text = text.translate(trans)

        text = ''.join(
            ch if not unicodedata.category(ch).startswith('C') or ch == '\n'
            else ' ' for ch in text
        )

        lines = text.split('\n')
        processed_lines = []

        for line in lines:
            line = self.RE_MULTI_WS.sub(' ', line).strip()
            processed_lines.append(line)

        text = '\n'.join(processed_lines)
        text = self.RE_MULTI_NEWLINES.sub('\n\n', text)
        text = text.strip()

        return text

    def purify_norm_text(self, texto_norma: Optional[str], texto_norma_actualizado: Optional[str], texto_resumido: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Purify all text fields of a norm including the summarized text"""
        purified_texto_norma = None
        purified_texto_actualizado = None
        purified_texto_resumido = None

        if texto_norma:
            purified_texto_norma = self.convert_html_to_structured_text(texto_norma)

        if texto_norma_actualizado:
            purified_texto_actualizado = self.convert_html_to_structured_text(texto_norma_actualizado)

        # Always purify texto_resumido if it exists, running the full pipeline
        if texto_resumido:
            purified_texto_resumido = self.convert_html_to_structured_text(texto_resumido)

        return purified_texto_norma, purified_texto_actualizado, purified_texto_resumido

    def purify_text(self, text: str) -> Optional[str]:
        """Clean and purify raw text content"""
        if not text or not text.strip():
            return None

        try:
            purified = self.convert_html_to_structured_text(text)
            return purified if purified and purified.strip() else None

        except Exception as e:
            self.logger.error(f"Error purifying text: {e}")
            return None

    def is_valid_text(self, text: str) -> bool:
        """Check if text is valid for processing"""
        if not text or not isinstance(text, str):
            return False

        stripped = text.strip()
        return len(stripped) > 10 and not stripped.isspace()
