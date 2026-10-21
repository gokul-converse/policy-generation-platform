
from pathlib import Path
from app.services.document_service import ingest_document

BASE_DIR = Path(__file__).resolve().parents[1]

pdf_path = BASE_DIR / "documents" / "hr" / "HRPolicy 1 2.pdf"

print("PDF path:", pdf_path)
print("File exists:", pdf_path.exists())

if not pdf_path.exists():
    raise FileNotFoundError(f"PDF not found: {pdf_path}")

result = ingest_document(
    file_path=str(pdf_path),
    domain="hr",
    approval_status="unknown",
    version="2025",
)

print("Ingestion result:", result)
