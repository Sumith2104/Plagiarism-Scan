import os
import mimetypes
from typing import Optional
from pypdf import PdfReader
import docx
from bs4 import BeautifulSoup
import pytesseract
from PIL import Image

def _detect_mime(file_path: str, content_type: str) -> str:
    """Detect MIME type using mimetypes module (no native libmagic needed)."""
    mime, _ = mimetypes.guess_type(file_path)
    if mime:
        return mime
    # Fallback to browser-provided content_type
    return content_type or "application/octet-stream"

class TextExtractor:
    @staticmethod
    def extract(file_path: str, content_type: str) -> str:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        detected_type = _detect_mime(file_path, content_type)

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
        # Source Code Support
        elif any(ext in detected_type for ext in ['python', 'javascript', 'java', 'c++', 'c source', 'ruby', 'php', 'go', 'rust']):
            return TextExtractor._extract_text(file_path)
        # Fallback for common code extensions if magic fails
        elif file_path.endswith(('.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs', '.php', '.rb')):
             return TextExtractor._extract_text(file_path)
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
                print("PDF text is empty, falling back to EasyOCR...")
                try:
                    import fitz  # PyMuPDF
                    import easyocr
                    from PIL import Image
                    import io
                    
                    # Initialize English reader. gpu=False is used to ensure compatibility 
                    # and avoid CUDA initialisation warnings on user environments.
                    import sys
                    try:
                        sys.stdout.reconfigure(encoding='utf-8')
                        sys.stderr.reconfigure(encoding='utf-8')
                    except Exception:
                        pass

                    reader_ocr = easyocr.Reader(['en'], gpu=False, verbose=False)
                    doc = fitz.open(file_path)
                    
                    for idx, page in enumerate(doc):
                        print(f"Running EasyOCR on PDF page {idx}...")
                        pix = page.get_pixmap()
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        
                        results = reader_ocr.readtext(img, detail=0)
                        if results:
                            text += " ".join(results) + "\n"
                    print("EasyOCR extraction complete!")
                except Exception as ocr_err:
                    print(f"OCR Fallback failed: {ocr_err}")
                
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
