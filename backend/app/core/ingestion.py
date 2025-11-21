import os
from typing import Optional
import magic
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image

class TextExtractor:
    @staticmethod
    def extract(file_path: str, content_type: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            mime = magic.Magic(mime=True)
            detected_type = mime.from_file(file_path)
        except Exception as e:
            print(f"Warning: Magic detection failed ({e}). Falling back to content_type.")
            detected_type = content_type

        # Fallback to provided content_type if detection is generic
        if detected_type == 'application/octet-stream':
            detected_type = content_type

        print(f"Detected type: {detected_type} for {file_path}")

        if 'pdf' in detected_type:
            return TextExtractor._extract_pdf(file_path)
        elif 'wordprocessingml' in detected_type or 'msword' in detected_type:
            return TextExtractor._extract_docx(file_path)
        elif 'html' in detected_type or 'xml' in detected_type:
            return TextExtractor._extract_html(file_path)
        elif 'text' in detected_type or 'plain' in detected_type:
            return TextExtractor._extract_text(file_path)
        elif 'image' in detected_type:
            return TextExtractor._extract_image(file_path)
        else:
            # Last resort fallback for unknown types that might be text
            try:
                return TextExtractor._extract_text(file_path)
            except:
                raise ValueError(f"Unsupported file type: {detected_type}")

    @staticmethod
    def _extract_pdf(file_path: str) -> str:
        text = ""
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            
            # Fallback to OCR if text is empty (scanned PDF)
            if not text.strip():
                # Note: This requires converting PDF pages to images first.
                # For MVP, we'll skip complex PDF-to-Image OCR and just return empty
                # or implement a simple warning.
                # To do this properly, we'd need pdf2image library.
                pass
                
        except Exception as e:
            print(f"Error extracting PDF: {e}")
        return text

    @staticmethod
    def _extract_docx(file_path: str) -> str:
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    @staticmethod
    def _extract_html(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f, 'html.parser')
            return soup.get_text(separator='\n')

    @staticmethod
    def _extract_text(file_path: str) -> str:
        encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # If all fail, use utf-8 with ignore
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()

    @staticmethod
    def _extract_image(file_path: str) -> str:
        try:
            return pytesseract.image_to_string(Image.open(file_path))
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
