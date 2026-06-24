from pypdf import PdfReader

def read_user_resume(path: str) -> str:
    """Extracts text content from a local resume file (PDF or TXT).
    """
    try:
        if path.endswith(".pdf"):
            reader = PdfReader(path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        else:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
    except Exception as e:
        return f"Error reading resume: {str(e)}"
