"""PDF text extraction service."""
import asyncio
from pathlib import Path
from typing import Optional

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None


async def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file using multiple strategies.
    
    Tries pdfplumber first (best for text-based PDFs),
    then pypdf, then OCR with Tesseract as fallback.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text content
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")
    
    # Try pdfplumber first (best for text extraction)
    text = await _extract_with_pdfplumber(path)
    if text and len(text.strip()) > 100:
        return text
    
    # Try pypdf as fallback
    text = await _extract_with_pypdf(path)
    if text and len(text.strip()) > 100:
        return text
    
    # Try OCR as last resort
    text = await _extract_with_ocr(path)
    if text:
        return text
    
    return ""


async def _extract_with_pdfplumber(file_path: Path) -> str:
    """Extract text using pdfplumber."""
    if pdfplumber is None:
        return ""
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _pdfplumber_sync, file_path)
    except Exception:
        return ""


def _pdfplumber_sync(file_path: Path) -> str:
    """Synchronous pdfplumber extraction."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
            # Also extract tables as text
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    text_parts.append(" | ".join(str(cell) if cell else "" for cell in row))
    return "\n\n".join(text_parts)


async def _extract_with_pypdf(file_path: Path) -> str:
    """Extract text using pypdf."""
    if pypdf is None:
        return ""
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _pypdf_sync, file_path)
    except Exception:
        return ""


def _pypdf_sync(file_path: Path) -> str:
    """Synchronous pypdf extraction."""
    text_parts = []
    with open(file_path, "rb") as f:
        reader = pypdf.PdfReader(f)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts)


async def _extract_with_ocr(file_path: Path) -> str:
    """Extract text using OCR (Tesseract)."""
    if pytesseract is None or Image is None:
        return ""
    
    try:
        # Convert PDF pages to images and OCR each
        import pdf2image
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _ocr_sync, file_path)
    except Exception:
        return ""


def _ocr_sync(file_path: Path) -> str:
    """Synchronous OCR extraction."""
    import pdf2image
    text_parts = []
    
    images = pdf2image.convert_from_path(file_path)
    for image in images:
        text = pytesseract.image_to_string(image, lang="por")
        if text.strip():
            text_parts.append(text)
    
    return "\n\n".join(text_parts)


async def extract_tables_from_pdf(file_path: str) -> list:
    """Extract tables from PDF as structured data."""
    if pdfplumber is None:
        return []
    
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _extract_tables_sync, file_path)
    except Exception:
        return []


def _extract_tables_sync(file_path: str) -> list:
    """Extract tables from PDF."""
    tables = []
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            for table_num, table in enumerate(page_tables):
                if table:
                    # Convert to list of dicts if headers exist
                    if table[0]:
                        headers = [str(h).strip() if h else f"col_{i}" for i, h in enumerate(table[0])]
                        rows = []
                        for row in table[1:]:
                            row_dict = {}
                            for i, cell in enumerate(row):
                                header = headers[i] if i < len(headers) else f"col_{i}"
                                row_dict[header] = str(cell).strip() if cell else ""
                            rows.append(row_dict)
                        tables.append({
                            "page": page_num + 1,
                            "table_index": table_num,
                            "headers": headers,
                            "rows": rows,
                        })
    return tables