
import asyncio
import re
import sys
from pathlib import Path

from pypdf import PdfReader
from sqlalchemy import delete, select

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import AsyncSessionLocal
from app.models import Document, DocumentChunk

DOCUMENT_DIR = BACKEND_DIR / "sample_documents"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

# Markdown headings: # Heading, ## Heading, etc.
MARKDOWN_HEADING_PATTERN = re.compile(
    r"^#{1,6}\s+(.+?)\s*#*\s*$"
)

# Numbered headings: 1. Leave Policy, 1.1 Annual Leave, etc.
NUMBERED_HEADING_PATTERN = re.compile(
    r"^\d+(?:\.\d+)*[.)]?\s+[A-Z][A-Za-z0-9 /&(),.'’():-]{1,110}$"
)

# Uppercase headings: LEAVE POLICY, COMPANY POLICY HANDBOOK, etc.
UPPERCASE_HEADING_PATTERN = re.compile(
    r"^[A-Z][A-Z0-9 /&(),.'’():-]{3,119}$"
)


def clean_text(text: str) -> str:
    """Normalize extracted text while preserving line breaks."""
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []

    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def detect_heading(line: str) -> str | None:
    """Detect Markdown, numbered, and uppercase headings."""
    line = line.strip()

    if not line or len(line) > 120:
        return None

    markdown_match = MARKDOWN_HEADING_PATTERN.match(line)
    if markdown_match:
        return markdown_match.group(1).strip()

    if NUMBERED_HEADING_PATTERN.match(line):
        return line

    if UPPERCASE_HEADING_PATTERN.match(line):
        return line

    return None


def split_into_chunks(text: str) -> list[str]:
    """Split text into overlapping chunks."""
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + CHUNK_SIZE, len(text))
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def split_page_into_sections(
    text: str,
    current_section: str | None = None,
) -> tuple[list[dict], str | None]:
    """Split page text by headings and retain section titles."""
    sections = []
    current_lines = []

    def save_section():
        content = "\n".join(current_lines).strip()

        if not content:
            return

        # Always assign a usable section title.
        section_title = current_section or "General"

        for chunk in split_into_chunks(content):
            sections.append(
                {
                    "section_title": section_title,
                    "chunk_text": chunk,
                }
            )

    for line in text.splitlines():
        line = line.strip()

        if not line:
            if current_lines:
                current_lines.append("")
            continue

        heading = detect_heading(line)

        if heading:
            save_section()
            current_section = heading
            current_lines = [line]
        else:
            current_lines.append(line)

    save_section()

    return sections, current_section


def extract_pages(file_path: Path) -> list[dict]:
    """Extract text from PDF pages or a TXT file."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf":
        reader = PdfReader(str(file_path))

        pages = [
            {
                "page_number": page_number,
                "text": clean_text(page.extract_text() or ""),
            }
            for page_number, page in enumerate(reader.pages, start=1)
        ]

    elif suffix == ".txt":
        text = clean_text(
            file_path.read_text(encoding="utf-8-sig")
        )

        pages = [
            {
                "page_number": 1,
                "text": text,
            }
        ]

    else:
        return []

    return [page for page in pages if page["text"]]


def document_settings(file_path: Path) -> dict:
    """Set document domain and approval status."""
    if file_path.name == "synthetic_company_policy.txt":
        return {
            "domain": "hr",
            "approval_status": "sample_not_approved",
        }

    return {
        "domain": "hr",
        "approval_status": "unknown",
    }


async def ingest_file(session, file_path: Path) -> int:
    """Ingest one document and replace its existing chunks."""
    pages = extract_pages(file_path)

    if not pages:
        print(
            f"SKIPPED: {file_path.name} — no extractable text"
        )
        return 0

    full_path = str(file_path.resolve())
    settings = document_settings(file_path)

    result = await session.execute(
        select(Document).where(
            Document.file_path == full_path,
            Document.version == "1",
        )
    )

    document = result.scalar_one_or_none()

    if document is None:
        document = Document(
            document_name=file_path.name,
            domain=settings["domain"],
            version="1",
            approval_status=settings["approval_status"],
            file_path=full_path,
            ingestion_status="processing",
        )

        session.add(document)
        await session.flush()

    else:
        document.document_name = file_path.name
        document.domain = settings["domain"]
        document.approval_status = settings["approval_status"]
        document.ingestion_status = "processing"

    # Remove old chunks before inserting refreshed chunks.
    await session.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document.document_id
        )
    )

    await session.flush()

    chunk_index = 0
    current_section = None

    for page in pages:
        sections, current_section = split_page_into_sections(
            page["text"],
            current_section,
        )

        for item in sections:
            session.add(
                DocumentChunk(
                    document_id=document.document_id,
                    chunk_index=chunk_index,
                    section_title=item["section_title"],
                    page_number=page["page_number"],
                    chunk_text=item["chunk_text"],
                )
            )

            chunk_index += 1

    document.ingestion_status = "completed"

    print(
        f"INGESTED: {file_path.name} | "
        f"pages={len(pages)} | chunks={chunk_index} | "
        f"approval_status={document.approval_status}"
    )

    return chunk_index


async def main():
    if not DOCUMENT_DIR.exists():
        raise FileNotFoundError(
            f"Folder not found: {DOCUMENT_DIR}"
        )

    files = sorted(
        path
        for path in DOCUMENT_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".txt"}
    )

    if not files:
        print("No PDF or TXT files found.")
        return

    async with AsyncSessionLocal() as session:
        try:
            total_chunks = 0

            for file_path in files:
                total_chunks += await ingest_file(
                    session,
                    file_path,
                )

            await session.commit()

            print("\nIngestion completed.")
            print(f"Files processed: {len(files)}")
            print(f"Chunks created: {total_chunks}")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
