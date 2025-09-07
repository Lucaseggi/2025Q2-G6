"""Text processing and purification functionality"""

import re
import unicodedata
from bs4 import BeautifulSoup, NavigableString
from typing import Optional, Tuple, List, Dict, Any


class TextProcessor:
    """Handles text purification and normalization"""
    
    # Common Unicode space-separators (Zs) and related
    UNICODE_SPACE_CHARS = (
        '\u00A0'  # NO-BREAK SPACE
        '\u1680'  # OGHAM SPACE MARK
        '\u2000'  # EN QUAD
        '\u2001'  # EM QUAD
        '\u2002'  # EN SPACE
        '\u2003'  # EM SPACE
        '\u2004'  # THREE-PER-EM SPACE
        '\u2005'  # FOUR-PER-EM SPACE
        '\u2006'  # SIX-PER-EM SPACE
        '\u2007'  # FIGURE SPACE
        '\u2008'  # PUNCTUATION SPACE
        '\u2009'  # THIN SPACE
        '\u200A'  # HAIR SPACE
        '\u202F'  # NARROW NO-BREAK SPACE
        '\u205F'  # MEDIUM MATHEMATICAL SPACE
        '\u3000'  # IDEOGRAPHIC SPACE
    )
    
    # Precompiled regex patterns
    RE_MULTI_WS = re.compile(r'\s+', flags=re.UNICODE)
    RE_MULTI_NEWLINES = re.compile(r'\n{3,}')  # Replace 3+ newlines with 2
    
    def __init__(self):
        """Initialize text processor"""
        self.ocr_fixes_applied = []
        self.purification_notes = []
    
    def normalize_ocr_artifacts(self, text: str, track_fixes: bool = True) -> str:
        """Replace common OCR artifacts and encoding issues with their proper counterparts."""
        if not text:
            return text
        
        original_text = text
        
        # Character replacement mapping
        replacements = {
            # Dashes (including various Unicode dash variants)
            '—': '-',  # em dash (U+2014) to regular dash
            '–': '-',  # en dash (U+2013) to regular dash
            '―': '-',  # horizontal bar (U+2015) to regular dash
            '−': '-',  # minus sign (U+2212) to regular dash
            
            # Quotes and apostrophes
            '"': '"',  # left double quote
            '"': '"',  # right double quote
            ''': "'",  # left single quote
            ''': "'",  # right single quote
            '´': "'",  # acute accent (often misused as apostrophe)
            '`': "'",  # grave accent (often misused as apostrophe)
            
            # Ellipsis
            '…': '...',  # horizontal ellipsis to three dots
            
            # Degree symbols (normalize to the standard degree symbol)
            'º': '°',  # masculine ordinal indicator to degree symbol
            
            # Accented characters with wrong direction tildes
            'À': 'Á',  # A with grave to A with acute
            'à': 'á',  # a with grave to a with acute
            'È': 'É',  # E with grave to E with acute
            'è': 'é',  # e with grave to e with acute
            'Ì': 'Í',  # I with grave to I with acute
            'ì': 'í',  # i with grave to i with acute
            'Ò': 'Ó',  # O with grave to O with acute
            'ò': 'ó',  # o with grave to o with acute
            'Ù': 'Ú',  # U with grave to U with acute
            'ù': 'ú',  # u with grave to u with acute
        }
        
        # Apply replacements and track fixes
        if track_fixes:
            for old_char, new_char in replacements.items():
                if old_char in text:
                    count = text.count(old_char)
                    text = text.replace(old_char, new_char)
                    self.ocr_fixes_applied.append(f"Replaced {count}x '{old_char}' → '{new_char}'")
        else:
            # Apply replacements without tracking
            for old_char, new_char in replacements.items():
                text = text.replace(old_char, new_char)
        
        return text
    
    def convert_html_to_structured_text(self, text: str) -> str:
        """
        Convert HTML to text while preserving structural information through line breaks.
        
        Strategy:
        - Block-level elements (P, DIV, BR) -> line breaks
        - Inline formatting (B, I, SPAN) -> preserve text, add minimal spacing
        - Preserve text content while maintaining document structure
        """
        if not text:
            return text
        
        # Fix common double-encoding symptom
        if '\u00C2\u00A0' in text:
            text = text.replace('\u00C2\u00A0', '\u00A0')
        
        # Parse HTML FIRST (this converts &#8212; to —)
        soup = BeautifulSoup(text, "html.parser")
        
        # Define block-level tags that should create line breaks
        BLOCK_TAGS = {
            'p', 'div', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'article', 'section', 'header', 'footer', 'nav', 'aside',
            'blockquote', 'pre', 'hr', 'ul', 'ol', 'li', 'dl', 'dt', 'dd'
        }
        
        # Define inline tags that should preserve text but may add minimal spacing
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
            
            # Add line break before block elements (except for the first element)
            if tag_name in BLOCK_TAGS:
                result.append('\n')
            
            # Process all children
            for child in element.children:
                child_text = process_element(child)
                if child_text:
                    result.append(child_text)
            
            # Add line break after block elements
            if tag_name in BLOCK_TAGS:
                result.append('\n')
            elif tag_name in INLINE_TAGS:
                # For inline elements, add a space to prevent word concatenation
                result.append(' ')
            
            return ''.join(result)
        
        # Process the entire document
        structured_text = process_element(soup)
        
        # Clean up whitespace first
        structured_text = self.normalize_whitespace_preserve_structure(structured_text)
        
        # THEN normalize OCR artifacts (after HTML entities are converted)
        structured_text = self.normalize_ocr_artifacts(structured_text)
        
        return structured_text
    
    def normalize_whitespace_preserve_structure(self, text: str) -> str:
        """Normalize whitespace while preserving line break structure for parsing."""
        if not text:
            return text
        
        # Translate various Unicode space separators to regular ASCII space
        trans = {ord(ch): ord(' ') for ch in self.UNICODE_SPACE_CHARS}
        text = text.translate(trans)
        
        # Replace control characters with space (except newlines)
        text = ''.join(
            ch if not unicodedata.category(ch).startswith('C') or ch == '\n' 
            else ' ' for ch in text
        )
        
        # Split by lines and process each line separately
        lines = text.split('\n')
        processed_lines = []
        
        for line in lines:
            # Collapse multiple spaces within each line, but preserve the line
            line = self.RE_MULTI_WS.sub(' ', line).strip()
            processed_lines.append(line)
        
        # Rejoin lines
        text = '\n'.join(processed_lines)
        
        # Remove excessive consecutive newlines (more than 2)
        text = self.RE_MULTI_NEWLINES.sub('\n\n', text)
        
        # Clean up leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def purify_norm_text(self, texto_norma: Optional[str], texto_norma_actualizado: Optional[str]) -> tuple[Optional[str], Optional[str]]:
        """Purify both text fields of a norm"""
        purified_texto_norma = None
        purified_texto_actualizado = None
        
        if texto_norma:
            purified_texto_norma = self.convert_html_to_structured_text(texto_norma)
        
        if texto_norma_actualizado:
            purified_texto_actualizado = self.convert_html_to_structured_text(texto_norma_actualizado)
        
        return purified_texto_norma, purified_texto_actualizado
    
    def purify_norm_with_tracking(self, norm_data: Dict[str, Any]) -> Dict[str, Any]:
        """Purify norm text and return comprehensive data for database storage"""
        # Reset tracking for this norm
        self.ocr_fixes_applied = []
        self.purification_notes = []
        
        source_id = norm_data.get('id')
        texto_norma = norm_data.get('texto_norma')
        texto_norma_actualizado = norm_data.get('texto_norma_actualizado')
        
        # Purify text fields
        purified_main_text = None
        purified_updated_text = None
        
        if texto_norma:
            purified_main_text = self.convert_html_to_structured_text(texto_norma)
            if purified_main_text != texto_norma:
                self.purification_notes.append("HTML structure normalized in main text")
        
        if texto_norma_actualizado:
            purified_updated_text = self.convert_html_to_structured_text(texto_norma_actualizado)
            if purified_updated_text != texto_norma_actualizado:
                self.purification_notes.append("HTML structure normalized in updated text")
        
        # Create combined text
        combined_text = self.get_combined_text(purified_main_text, purified_updated_text)
        text_length = len(combined_text) if combined_text else 0
        
        # Prepare purification data with ALL original fields
        purification_data = {
            'source_id': source_id,
            
            # All original fields from normas table
            'infoleg_id': norm_data.get('infoleg_id'),
            'jurisdiccion': norm_data.get('jurisdiccion'),
            'clase_norma': norm_data.get('clase_norma'),
            'tipo_norma': norm_data.get('tipo_norma'),
            'sancion': norm_data.get('sancion'),
            'id_normas': norm_data.get('id_normas'),
            'publicacion': norm_data.get('publicacion'),
            'titulo_sumario': norm_data.get('titulo_sumario'),
            'titulo_resumido': norm_data.get('titulo_resumido'),
            'observaciones': norm_data.get('observaciones'),
            'nro_boletin': norm_data.get('nro_boletin'),
            'pag_boletin': norm_data.get('pag_boletin'),
            'texto_resumido': norm_data.get('texto_resumido'),
            'estado': norm_data.get('estado'),
            'lista_normas_que_complementa': norm_data.get('lista_normas_que_complementa'),
            'lista_normas_que_la_complementan': norm_data.get('lista_normas_que_la_complementan'),
            
            # Original text fields (preserved as-is)
            'texto_norma': texto_norma,
            'texto_norma_actualizado': texto_norma_actualizado,
            
            # Purified text fields
            'purified_main_text': purified_main_text,
            'purified_updated_text': purified_updated_text,
            'combined_text': combined_text,
            'text_length': text_length,
            
            # Purification metadata
            'ocr_fixes_applied': self.ocr_fixes_applied.copy(),
            'purification_notes': '; '.join(self.purification_notes) if self.purification_notes else 'No specific issues found'
        }
        
        return purification_data
    
    def get_combined_text(self, texto_norma: Optional[str], texto_norma_actualizado: Optional[str]) -> str:
        """Combine both text fields into a single text for processing"""
        parts = []
        
        if texto_norma:
            parts.append(f"TEXTO NORMA:\n{texto_norma}")
        
        if texto_norma_actualizado:
            parts.append(f"TEXTO NORMA ACTUALIZADO:\n{texto_norma_actualizado}")
        
        return "\n\n".join(parts) if parts else ""