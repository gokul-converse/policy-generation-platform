import asyncio
import re
import sys
from pathlib import Path

# Add backend root to Python import path
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from pypdf import PdfReader
from sqlalchemy import select, delete

from app.db.session import AsyncSessionLocal
from app.models import Document, DocumentChunk

BACKEND_DIR = Path(__file__).resolve().parent.parent
DOCUMENT_DIR = BACKEND_DIR / "sample_documents"

PDF_NAME = "HRPolicy 1 2.pdf"
SAMPLE_TXT_NAME = "synthetic_company_policy.txt"

CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200

HEADING_PATTERN = re.compile(
    r"^\s*(?:"
    r"\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z0-9 /&(),.'-]{2,}"
    r"|[A-Z][A-Z0-9 /&(),.'-]{4,}"
    r")\s*$"
)


def clean_text(text: str) -> str:
    """Normalize extracted text without removing line boundaries."""
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

    return "\n".join(lines).strip()


def split_into_chunks(text: str) -> list[str]:
    """Split section content into overlapping character-based chunks."""
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + CHUNK_SIZE, text_length)
        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= text_length:
            break

        start = end - CHUNK_OVERLAP

    return chunks


def is_heading(line: str) -> bool:
    """Identify likely numbered or uppercase section headings."""
    line = line.strip()

    if not line or len(line) > 120:
        return False

    return bool(HEADING_PATTERN.match(line))


def split_page_into_sections(
    text: str,
    current_section: str | None = None,
) -> tuple[list[dict], str | None]:
    """
    Split extracted page text into sections.

    The current section is carried across pages when a heading
    does not appear at the beginning of the next page.
    """
    sections = []
    current_lines = []

    def save_current_section():
        content = "\n".join(current_lines).strip()

        if not content:
            return

        for chunk in split_into_chunks(content):
            sections.append(
                {
                    "section_title": current_section,
                    "chunk_text": chunk,
                }
            )

    for line in text.splitlines():
        line = line.strip()

        if not line:
            if current_lines:
                current_lines.append("")
            continue

        if is_heading(line):
            save_current_section()
            current_section = line
            current_lines = [line]
        else:
            current_lines.append(line)

    save_current_section()

    return sections, current_section


def extract_pdf_pages(file_path: Path) -> list[dict]:
    """Extract text page by page from a PDF."""
    reader = PdfReader(str(file_path))
    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")

        if text:
            pages.append(
                {
                    "page_number": page_number,
                    "text": text,
                }
            )

    return pages


def extract_txt_pages(file_path: Path) -> list[dict]:
    """Treat a text file as a single page."""
    text = file_path.read_text(encoding="utf-8-sig")
    text = clean_text(text)

    if not text:
        return []

    return [{"page_number": 1, "text": text}]


def get_document_settings(file_path: Path) -> dict:
    """Set metadata according to the input file."""
    if file_path.name == SAMPLE_TXT_NAME:
        return {
            "domain": "hr",
            "approval_status": "sample_not_approved",
        }

    return {
        "domain": "hr",
        "approval_status": "unknown",
    }


async def ingest_file(session, file_path: Path) -> tuple[str, int]:
    """Create or update a document and its chunks."""

    if file_path.suffix.lower() == ".pdf":
        pages = extract_pdf_pages(file_path)
    elif file_path.suffix.lower() == ".txt":
        pages = extract_txt_pages(file_path)
    else:
        print(f"SKIPPED: Unsupported file type: {file_path.name}")
        return "skipped", 0

    if not pages:
        raise ValueError(f"No extractable text found in {file_path.name}")

    file_path_string = str(file_path.resolve())
    settings = get_document_settings(file_path)

    result = await session.execute(
        select(Document).where(
            Document.file_path == file_path_string,
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
            file_path=file_path_string,
            ingestion_status="processing",
        )
        session.add(document)
        await session.flush()
    else:
        document.document_name = file_path.name
        document.domain = settings["domain"]
        document.approval_status = settings["approval_status"]
        document.ingestion_status = "processing"

    # Remove old chunks so re-ingestion does not create duplicates.
    await session.execute(
        delete(DocumentChunk).where(
            DocumentChunk.document_id == document.document_id
        )
    )
    await session.flush()

    chunk_index = 0
    current_section = None

    for page in pages:
        page_sections, current_section = split_page_into_sections(
            page["text"],
            current_section=current_section,
        )

        for item in page_sections:
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

    await session.flush()

    print(
        f"INGESTED: {file_path.name} | "
        f"pages={len(pages)} | "
        f"chunks={chunk_index} | "
        f"approval_status={document.approval_status}"
    )

    return "ingested", chunk_index


async def main():
    if not DOCUMENT_DIR.exists():
        raise FileNotFoundError(
            f"Document folder not found: {DOCUMENT_DIR}"
        )

    file_paths = [
        DOCUMENT_DIR / PDF_NAME,
        DOCUMENT_DIR / SAMPLE_TXT_NAME,
    ]

    async with AsyncSessionLocal() as session:
        try:
            total_ingested = 0
            total_chunks = 0
            total_skipped = 0

            for file_path in file_paths:
                if not file_path.exists():
                    print(f"NOT FOUND: {file_path.name}")
                    continue

                status, chunks = await ingest_file(session, file_path)

                if status == "ingested":
                    total_ingested += 1
                    total_chunks += chunks
                else:
                    total_skipped += 1

            await session.commit()

            print("\nDocument ingestion finished.")
            print(f"Documents ingested/updated: {total_ingested}")
            print(f"Documents skipped: {total_skipped}")
            print(f"Chunks created: {total_chunks}")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
