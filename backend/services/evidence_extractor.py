"""Safe, deterministic, non-AI extractor for industrial evidence artifacts.
Extracts basic structural metadata and preview data without making causal inferences.
Uploaded files are treated strictly as untrusted DATA.
"""
import csv
import io
import struct
from typing import Any, Dict

def extract_csv_metadata(content: bytes) -> Dict[str, Any]:
    """Deterministically parses CSV files, extracting column headers and sample preview rows."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        text = content.decode("latin-1", errors="replace")

    reader = csv.reader(io.StringIO(text))
    rows = []
    headers = []
    total_rows = 0

    try:
        for idx, row in enumerate(reader):
            if idx == 0:
                headers = [str(col).strip() for col in row]
            else:
                if len(rows) < 5 and row:
                    # Create preview dict row if headers available
                    if headers and len(row) == len(headers):
                        rows.append({headers[i]: row[i] for i in range(len(headers))})
                    else:
                        rows.append({f"col_{i}": val for i, val in enumerate(row)})
                total_rows += 1
    except Exception as e:
        return {
            "format": "csv",
            "parse_error": f"Partial CSV parsing error: {str(e)}",
            "columns": headers,
            "row_count": total_rows,
            "preview_rows": rows,
        }

    return {
        "format": "csv",
        "columns": headers,
        "row_count": total_rows,
        "preview_rows": rows,
    }

def extract_txt_metadata(content: bytes) -> Dict[str, Any]:
    """Safely extracts text snippets from plain text logs or field notes."""
    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        text = content.decode("latin-1", errors="replace")

    # Sanitize and truncate to safe preview
    clean_preview = text[:2000].strip()
    return {
        "format": "text",
        "char_count": len(text),
        "line_count": text.count("\n") + 1,
        "preview_text": clean_preview,
    }

def extract_pdf_metadata(content: bytes) -> Dict[str, Any]:
    """Safely registers PDF documents and extracts plain text if a safe parser is available."""
    is_valid_header = content.startswith(b"%PDF-")
    meta: Dict[str, Any] = {
        "format": "pdf",
        "valid_header": is_valid_header,
        "pages": None,
        "preview_text": None,
    }

    # Optional pypdf / pypdf2 extraction if installed in container
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content))
        meta["pages"] = len(reader.pages)
        if len(reader.pages) > 0:
            extracted = reader.pages[0].extract_text() or ""
            meta["preview_text"] = extracted[:2000].strip()
    except Exception:
        # If pypdf is not installed, register cleanly without crashing
        pass

    return meta

def extract_image_metadata(content: bytes, ext: str) -> Dict[str, Any]:
    """Extracts width, height, and format metadata from JPG/PNG images safely using header bytes."""
    width = None
    height = None
    image_format = ext.lower().replace(".", "")

    try:
        # Check PNG header
        if content.startswith(b"\x89PNG\r\n\x1a\n") and len(content) >= 24:
            # IHDR chunk dimensions are at offset 16-24
            w, h = struct.unpack(">II", content[16:24])
            width, height = int(w), int(h)
            image_format = "png"
        # Check JPEG header
        elif content.startswith(b"\xff\xd8\xff"):
            image_format = "jpeg"
            # Parse JPEG SOF segments for dimensions
            idx = 2
            size = len(content)
            while idx < size - 8:
                if content[idx] != 0xFF:
                    idx += 1
                    continue
                marker = content[idx + 1]
                # SOF0, SOF1, SOF2 markers contain height and width
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                    h, w = struct.unpack(">HH", content[idx + 5 : idx + 9])
                    width, height = int(w), int(h)
                    break
                else:
                    # Skip segment
                    segment_len = struct.unpack(">H", content[idx + 2 : idx + 4])[0]
                    idx += 2 + segment_len
    except Exception:
        pass

    # Optional Pillow fallback if available
    if width is None or height is None:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(content))
            width, height = img.size
        except Exception:
            pass

    return {
        "format": "image",
        "image_type": image_format,
        "width": width,
        "height": height,
    }

def extract_evidence_metadata(content: bytes, filename: str) -> Dict[str, Any]:
    """Route extraction deterministically based on file extension."""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext == ".csv":
        return extract_csv_metadata(content)
    elif ext == ".txt":
        return extract_txt_metadata(content)
    elif ext == ".pdf":
        return extract_pdf_metadata(content)
    elif ext in (".jpg", ".jpeg", ".png"):
        return extract_image_metadata(content, ext)
    else:
        return {"format": "unknown"}
