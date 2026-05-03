"""Ingest product PDFs and property markdown files from GCS into Firestore vector index.

Reads PDFs and .md files from the GCS knowledge bucket, extracts/parses text,
chunks, generates embeddings, and stores in Firestore knowledge_chunks
collection for RAG retrieval.

PDFs: text extracted via Gemini Flash, fixed-size chunks (800 chars, 200 overlap).
.md files: parsed by ## section headers — each section becomes one chunk with
           rich property metadata (section_type, price_range, property_type, etc.).

Current approach: Gemini Flash (Part.from_bytes) for PDF text extraction.
This works well for a small corpus (10-20 PDFs) with minimal setup.

Usage:
    # Ingest all PDFs (default bucket)
    uv run python scripts/ingest_knowledge.py

    # Custom bucket
    uv run python scripts/ingest_knowledge.py --bucket my-bucket

    # Dry run (extract + chunk, skip Firestore writes)
    uv run python scripts/ingest_knowledge.py --dry-run

    # Single collection only
    uv run python scripts/ingest_knowledge.py --collection calden

    # Wipe existing chunks before ingesting
    uv run python scripts/ingest_knowledge.py --clear

    # Re-ingest all files even if unchanged
    uv run python scripts/ingest_knowledge.py --force

Incremental mode (default):
    By default, the script compares GCS blob update timestamps against
    Firestore metadata. Only new or updated files are re-ingested.
    Use --force or --clear to override.

Scaling to Document AI:
    When the corpus grows beyond ~50 PDFs or needs production-grade consistency,
    migrate text extraction from Gemini to Google Document AI:

    1. Enable the Document AI API in GCP Console.
    2. Create a "Document OCR" processor in the target region.
    3. Add dependency: google-cloud-documentai>=3.0.0
    4. Replace extract_text_from_pdf() with a Document AI call:

        from google.cloud import documentai_v1 as documentai

        def extract_text_docai(pdf_bytes: bytes, project_id: str,
                               location: str, processor_id: str) -> str:
            client = documentai.DocumentProcessorServiceClient()
            name = client.processor_path(project_id, location, processor_id)
            raw_doc = documentai.RawDocument(content=pdf_bytes,
                                             mime_type="application/pdf")
            request = documentai.ProcessRequest(name=name, raw_document=raw_doc)
            result = client.process_document(request=request)
            return result.document.text

    5. For batch processing (100+ PDFs), use batch_process_documents()
       with GCS input/output URIs instead of inline bytes.

    Benefits: deterministic output, better table extraction, handles
    scanned PDFs via OCR, per-page pricing ($0.01-0.065/page).

Automating with Cloud Function (GCS trigger):
    To replace manual runs with automatic ingestion on GCS upload:

    1. Create a Cloud Function (Gen 2) triggered by google.cloud.storage.object.v1.finalized
       on the sales-trainer-knowledge bucket.
    2. The function receives the event with bucket/object name, downloads the PDF,
       and runs the same extract -> chunk -> embed -> store pipeline for that single file.
    3. Delete old chunks for the file first (delete_chunks_for_file pattern).
    4. Terraform resource:

        resource "google_cloudfunctions2_function" "ingest_knowledge" {
          name     = "ingest-knowledge"
          location = "us-central1"
          build_config { runtime = "python311"; entry_point = "handle_gcs_event" }
          service_config {
            available_memory = "512Mi"
            timeout_seconds  = 300
            environment_variables = {
              GEMINI_API_KEY      = "..."
              FIRESTORE_DATABASE  = "ai-ml-native"
            }
          }
          event_trigger {
            event_type   = "google.cloud.storage.object.v1.finalized"
            trigger_region = "us-central1"
            event_filters { attribute = "bucket"; value = "sales-trainer-knowledge" }
          }
        }
"""

import argparse
import asyncio
import logging
import os
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from google import genai
from google.cloud import firestore, storage
from google.genai import types

# Load .env from backend directory so GEMINI_API_KEY is available
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_BUCKET = "sales-trainer-knowledge"
GCS_PREFIX = "products/"
FIRESTORE_COLLECTION = "knowledge_chunks"

EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 2048  # Must match Firestore vector index dimension (max 2048)
EXTRACTION_MODEL = "gemini-2.0-flash"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 200

# Map PDF filenames to collection metadata.
# Key substring in filename -> (collection_id, doc_type)
COLLECTION_MAP: dict[str, tuple[str, str]] = {
    "Bracken": ("bracken", ""),
    "Calden": ("calden", ""),
    "Modero": ("modero", ""),
    "Neo": ("neo", ""),
    "NEO": ("neo", ""),
    "Whitehaven": ("whitehaven", ""),
}

DOC_TYPE_MAP: dict[str, str] = {
    "Training Guide": "training_guide",
    "Selling Sheet": "selling_sheet",
}

# Property .md file metadata: filename key substring -> property metadata dict
PROPERTY_MAP: dict[str, dict[str, str]] = {
    "Property_1": {
        "property_id": "property_1",
        "property_name": "Maple Grove Starter Home",
        "price_range": "budget",
        "property_type": "single_family",
    },
    "Property_2": {
        "property_id": "property_2",
        "property_name": "Ridgmont Luxury Estate",
        "price_range": "premium",
        "property_type": "single_family",
    },
    "Property_3": {
        "property_id": "property_3",
        "property_name": "Elm Street Fixer-Upper",
        "price_range": "budget",
        "property_type": "single_family",
    },
    "Property_4": {
        "property_id": "property_4",
        "property_name": "Innovation Park New Construction",
        "price_range": "mid_market",
        "property_type": "single_family",
    },
    "Property_5": {
        "property_id": "property_5",
        "property_name": "Park Avenue Investment Property",
        "price_range": "mid_market",
        "property_type": "single_family",
    },
    "Property_6": {
        "property_id": "property_6",
        "property_name": "Urban Lofts Condo",
        "price_range": "budget",
        "property_type": "condo",
    },
    "Property_7": {
        "property_id": "property_7",
        "property_name": "Clearwater Family Home",
        "price_range": "premium",
        "property_type": "single_family",
    },
    "Property_8": {
        "property_id": "property_8",
        "property_name": "Lakeside Waterfront Estate",
        "price_range": "premium",
        "property_type": "waterfront",
    },
    "Property_9": {
        "property_id": "property_9",
        "property_name": "Rolling Meadows Acreage",
        "price_range": "mid_market",
        "property_type": "acreage",
    },
    "Property_10": {
        "property_id": "property_10",
        "property_name": "Commerce Street Duplex",
        "price_range": "mid_market",
        "property_type": "duplex",
    },
    "Property_Index": {
        "property_id": "property_index",
        "property_name": "Property Index Summary",
        "price_range": "",
        "property_type": "index",
    },
}

# Markdown section header -> section_type slug for metadata
SECTION_TYPE_MAP: dict[str, str] = {
    "PROPERTY IDENTITY": "property_identity",
    "NEIGHBORHOOD PROFILE": "neighborhood_profile",
    "PROPERTY DESCRIPTION": "property_description",
    "KEY FEATURES & SELLING POINTS": "key_features",
    "SCHOOL INFORMATION": "school_information",
    "NEARBY AMENITIES & FEATURES": "amenities",
    "BUYER PERSONALITY FIT": "buyer_fit",
    "OBJECTION HANDLERS & TALKING POINTS": "objection_handlers",
    "COMPARABLE HOMES (Light Comps)": "comparable_homes",
    "COMPARABLE HOMES": "comparable_homes",
    "AGENT TALKING POINTS (Memorize These)": "agent_talking_points",
    "AGENT TALKING POINTS": "agent_talking_points",
    "INSPECTION RED FLAGS TO EXPECT": "inspection_flags",
    "FINANCING TALKING POINTS": "financing",
    "TIMELINE & URGENCY": "timeline",
    "FOLLOW-UP QUESTIONS FOR BUYERS (If they go quiet)": "followup_questions",
    "FOLLOW-UP QUESTIONS FOR BUYERS": "followup_questions",
    "CLOSING NOTES": "closing_notes",
}


def detect_metadata(filename: str) -> tuple[str, str]:
    """Extract collection ID and doc type from a PDF filename.

    Args:
        filename: The PDF filename (e.g., 'Calden Training Guide V1.pdf')

    Returns:
        Tuple of (collection_id, doc_type)
    """
    collection_id = "unknown"
    for key, (cid, _) in COLLECTION_MAP.items():
        if key.lower() in filename.lower():
            collection_id = cid
            break

    doc_type = "unknown"
    for key, dtype in DOC_TYPE_MAP.items():
        if key.lower() in filename.lower():
            doc_type = dtype
            break

    return collection_id, doc_type


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Maximum characters per chunk
        overlap: Overlapping characters between chunks

    Returns:
        List of text chunks (empty strings filtered out)
    """
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def chunk_by_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (section_title, section_content) pairs on ## headers.

    Each ## header starts a new chunk. Content before the first ## is grouped
    under the document's # title (or "Introduction" if no title found).

    Args:
        text: Full markdown text

    Returns:
        List of (section_title, section_content) tuples, empty sections excluded
    """
    sections: list[tuple[str, str]] = []
    current_title = "Introduction"
    current_lines: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            content = "\n".join(current_lines).strip()
            if content:
                sections.append((current_title, content))
            current_title = line[3:].strip()
            current_lines = [line]
        elif line.startswith("# ") and not current_lines:
            current_title = line[2:].strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    content = "\n".join(current_lines).strip()
    if content:
        sections.append((current_title, content))

    return sections


# ---------------------------------------------------------------------------
# GCS helpers
# ---------------------------------------------------------------------------


def list_knowledge_files(bucket_name: str, prefix: str = GCS_PREFIX) -> list[storage.Blob]:
    """List all PDF and markdown blobs in the GCS bucket under the given prefix."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=prefix))
    return [b for b in blobs if b.name.lower().endswith((".pdf", ".md"))]


def download_pdf_bytes(blob: storage.Blob) -> bytes:
    """Download a PDF blob as raw bytes."""
    return blob.download_as_bytes()


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------


async def extract_text_from_pdf(client: genai.Client, pdf_bytes: bytes, filename: str) -> str:
    """Use Gemini to extract text content from a PDF.

    Args:
        client: Gemini client
        pdf_bytes: Raw PDF file bytes
        filename: Filename for logging

    Returns:
        Extracted text content
    """
    logger.info(f"  Extracting text from {filename} ({len(pdf_bytes):,} bytes)...")

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=EXTRACTION_MODEL,
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    (
                        "Extract ALL text content from this PDF document. "
                        "Return the complete text preserving the structure and formatting. "
                        "Include all product names, features, specifications, prices, and details. "
                        "Do not summarize -- return the full text."
                    ),
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    max_output_tokens=8192,
                ),
            )
            break
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                wait = 30 * (attempt + 1)
                logger.warning(f"  Rate limited, retrying in {wait}s (attempt {attempt + 1})...")
                await asyncio.sleep(wait)
            else:
                raise

    text = response.text or ""
    # Clean up markdown artifacts from Gemini output
    text = re.sub(r"^```\w*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    logger.info(f"  Extracted {len(text):,} characters from {filename}")
    return text


async def generate_embedding(client: genai.Client, text: str) -> list[float]:
    """Generate embedding vector for a text chunk.

    Args:
        client: Gemini client
        text: Text to embed

    Returns:
        768-dimensional embedding vector
    """
    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSIONS),
    )
    if not response.embeddings or response.embeddings[0].values is None:
        raise ValueError("No embedding returned from API")
    return list(response.embeddings[0].values)


# ---------------------------------------------------------------------------
# Firestore helpers
# ---------------------------------------------------------------------------


async def clear_collection(db: firestore.AsyncClient, collection_name: str) -> int:
    """Delete all documents in a Firestore collection.

    Args:
        db: Async Firestore client
        collection_name: Collection to clear

    Returns:
        Number of documents deleted
    """
    docs = await db.collection(collection_name).get()
    count = 0
    for doc in docs:
        await doc.reference.delete()
        count += 1
    return count


async def get_indexed_timestamps(
    db: firestore.AsyncClient,
    collection_name: str,
) -> dict[str, str]:
    """Get the latest created_at timestamp per source_file in the index.

    Returns:
        Dict mapping source_file -> created_at ISO string
    """
    docs = await db.collection(collection_name).get()
    timestamps: dict[str, str] = {}
    for doc in docs:
        data = doc.to_dict()
        meta = data.get("metadata", {})
        source = meta.get("source_file", "")
        created = meta.get("created_at", "")
        if source and (source not in timestamps or created > timestamps[source]):
            timestamps[source] = created
    return timestamps


async def delete_chunks_for_file(
    db: firestore.AsyncClient,
    collection_name: str,
    source_file: str,
) -> int:
    """Delete all chunks for a given source file.

    Args:
        db: Async Firestore client
        collection_name: Collection to delete from
        source_file: The source_file metadata value to match

    Returns:
        Number of documents deleted
    """
    docs = (
        await db.collection(collection_name).where("metadata.source_file", "==", source_file).get()
    )
    count = 0
    for doc in docs:
        await doc.reference.delete()
        count += 1
    return count


async def store_chunk(
    db: firestore.AsyncClient,
    chunk_id: str,
    content: str,
    embedding: list[float],
    metadata: dict[str, str | int],
) -> None:
    """Store a single chunk with embedding in Firestore.

    Args:
        db: Async Firestore client
        chunk_id: Unique chunk identifier
        content: Text content of the chunk
        embedding: Embedding vector
        metadata: Metadata dict (category, source_file, doc_type, etc.)
    """
    from google.cloud.firestore_v1.base_vector_query import Vector  # type: ignore[import-untyped]

    doc_ref = db.collection(FIRESTORE_COLLECTION).document(chunk_id)
    await doc_ref.set(
        {
            "chunk_id": chunk_id,
            "content": content,
            "embedding": Vector(embedding),
            "metadata": metadata,
        }
    )


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------


async def ingest_pdf(
    gemini_client: genai.Client,
    db: firestore.AsyncClient,
    blob: storage.Blob,
    dry_run: bool = False,
) -> int:
    """Ingest a single PDF: extract text, chunk, embed, store.

    Args:
        gemini_client: Gemini client for extraction + embedding
        db: Async Firestore client
        blob: GCS blob to process
        dry_run: If True, skip Firestore writes

    Returns:
        Number of chunks stored
    """
    filename = blob.name.split("/")[-1]
    collection_id, doc_type = detect_metadata(filename)

    logger.info(f"Processing: {filename}")
    logger.info(f"  Collection: {collection_id}, Type: {doc_type}")

    # 1. Download PDF bytes from GCS
    pdf_bytes = download_pdf_bytes(blob)

    # 2. Extract text via Gemini
    text = await extract_text_from_pdf(gemini_client, pdf_bytes, filename)
    if not text.strip():
        logger.warning(f"  No text extracted from {filename}, skipping")
        return 0

    # 3. Chunk
    chunks = chunk_text(text)
    logger.info(f"  Created {len(chunks)} chunks")

    if dry_run:
        for i, chunk in enumerate(chunks):
            logger.info(f"  Chunk {i}: {chunk[:80]}...")
        return len(chunks)

    # 4. Embed and store each chunk
    stored = 0
    for i, chunk in enumerate(chunks):
        chunk_id = f"{collection_id}_{doc_type}_{i:03d}"

        # Rate limiting: Gemini embedding API has per-minute quotas
        if i > 0 and i % 50 == 0:
            logger.info(f"  Rate limit pause at chunk {i}...")
            await asyncio.sleep(5)

        try:
            embedding = await generate_embedding(gemini_client, chunk)

            metadata = {
                "source_file": filename,
                "category": collection_id,
                "doc_type": doc_type,
                "chunk_index": i,
                "created_at": datetime.now(UTC).isoformat(),
            }

            await store_chunk(db, chunk_id, chunk, embedding, metadata)
            stored += 1
        except Exception as e:
            logger.error(f"  Failed to process chunk {i}: {e}")
            continue

    logger.info(f"  Stored {stored}/{len(chunks)} chunks for {filename}")
    return stored


async def ingest_md(
    gemini_client: genai.Client,
    db: firestore.AsyncClient,
    blob: storage.Blob,
    dry_run: bool = False,
) -> int:
    """Ingest a markdown property file: parse sections, embed, store.

    Unlike PDFs, no text extraction is needed — the file is read directly.
    Chunking is section-based (## headers) rather than fixed-size, preserving
    the semantic structure of each property document.

    Args:
        gemini_client: Gemini client for embedding generation
        db: Async Firestore client
        blob: GCS blob to process
        dry_run: If True, skip Firestore writes

    Returns:
        Number of section chunks stored
    """
    filename = blob.name.split("/")[-1]

    # Resolve property metadata from filename
    property_meta: dict[str, str] = {}
    # Sort by key length descending so Property_10 matches before Property_1
    for key, meta in sorted(PROPERTY_MAP.items(), key=lambda x: len(x[0]), reverse=True):
        if key.lower() in filename.lower():
            property_meta = meta
            break

    if not property_meta:
        property_meta = {
            "property_id": "unknown",
            "property_name": filename.replace(".md", ""),
            "price_range": "",
            "property_type": "unknown",
        }

    collection_id = property_meta["property_id"]
    logger.info(f"Processing: {filename}")
    logger.info(f"  Property: {property_meta['property_name']} ({collection_id})")

    # Download and decode markdown text directly (no Gemini extraction needed)
    text = blob.download_as_text(encoding="utf-8")

    sections = chunk_by_sections(text)
    logger.info(f"  Created {len(sections)} section chunks")

    if dry_run:
        for title, content in sections:
            logger.info(f"  Section '{title}': {len(content)} chars")
        return len(sections)

    stored = 0
    for i, (section_title, section_content) in enumerate(sections):
        section_slug = SECTION_TYPE_MAP.get(
            section_title,
            re.sub(r"[^a-z0-9]+", "_", section_title.lower()).strip("_"),
        )
        chunk_id = f"{collection_id}_{section_slug}"

        if i > 0 and i % 50 == 0:
            logger.info(f"  Rate limit pause at chunk {i}...")
            await asyncio.sleep(5)

        try:
            embedding = await generate_embedding(gemini_client, section_content)

            metadata: dict[str, str | int] = {
                "source_file": filename,
                "category": collection_id,
                "doc_type": "property_listing",
                "section_type": section_slug,
                "section_title": section_title,
                "property_id": property_meta["property_id"],
                "property_name": property_meta["property_name"],
                "price_range": property_meta["price_range"],
                "property_type": property_meta["property_type"],
                "chunk_index": i,
                "created_at": datetime.now(UTC).isoformat(),
            }

            await store_chunk(db, chunk_id, section_content, embedding, metadata)
            stored += 1
        except Exception as e:
            logger.error(f"  Failed to process section '{section_title}': {e}")
            continue

    logger.info(f"  Stored {stored}/{len(sections)} sections for {filename}")
    return stored


async def run(args: argparse.Namespace) -> None:
    """Run the ingestion pipeline."""
    logger.info(f"Scanning gs://{args.bucket}/{GCS_PREFIX}")
    blobs = list_knowledge_files(args.bucket)

    if not blobs:
        logger.error("No knowledge files (PDF or .md) found in bucket")
        sys.exit(1)

    logger.info(f"Found {len(blobs)} files:")
    for b in blobs:
        logger.info(f"  - {b.name}")

    # Filter to single collection if requested
    if args.collection:
        blobs = [b for b in blobs if args.collection.lower() in b.name.lower()]
        if not blobs:
            logger.error(f"No files found matching collection '{args.collection}'")
            sys.exit(1)
        logger.info(f"Filtered to {len(blobs)} files for collection '{args.collection}'")

    # Initialize clients
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.error("GEMINI_API_KEY not set. Add it to backend/.env or export it.")
        sys.exit(1)
    gemini_client = genai.Client(api_key=api_key)
    firestore_db = os.environ.get("FIRESTORE_DATABASE", "(default)")
    db = firestore.AsyncClient(database=firestore_db)
    logger.info(f"Using Firestore database: {firestore_db}")

    # Clear existing data if requested
    if args.clear and not args.dry_run:
        logger.info(f"Clearing existing {FIRESTORE_COLLECTION} collection...")
        deleted = await clear_collection(db, FIRESTORE_COLLECTION)
        logger.info(f"Deleted {deleted} existing documents")

    # Incremental mode: check which files need re-indexing
    indexed_timestamps: dict[str, str] = {}
    if not args.clear and not args.force:
        logger.info("Checking for already-indexed files...")
        indexed_timestamps = await get_indexed_timestamps(db, FIRESTORE_COLLECTION)

    total_chunks = 0
    skipped = 0
    start = time.time()

    for i, blob in enumerate(blobs):
        filename = blob.name.split("/")[-1]

        # Skip files that haven't changed since last indexing
        if filename in indexed_timestamps and not args.force:
            blob_updated = blob.updated
            if blob_updated:
                indexed_at = indexed_timestamps[filename]
                blob_updated_iso = blob_updated.isoformat()
                if blob_updated_iso <= indexed_at:
                    logger.info(f"Skipping {filename} (unchanged since last index)")
                    skipped += 1
                    continue
                # File changed -- delete old chunks before re-ingesting
                logger.info(f"File changed: {filename}, deleting old chunks...")
                deleted = await delete_chunks_for_file(db, FIRESTORE_COLLECTION, filename)
                logger.info(f"  Deleted {deleted} old chunks")

        if filename.lower().endswith(".md"):
            chunks = await ingest_md(gemini_client, db, blob, dry_run=args.dry_run)
        else:
            chunks = await ingest_pdf(gemini_client, db, blob, dry_run=args.dry_run)

        total_chunks += chunks
        if i < len(blobs) - 1:
            logger.info("  Pausing 10s between files for rate limits...")
            await asyncio.sleep(10)

    elapsed = time.time() - start
    mode = "DRY RUN" if args.dry_run else "COMPLETE"
    logger.info(
        f"\n{mode}: {total_chunks} chunks from {len(blobs) - skipped} files in {elapsed:.1f}s"
    )
    if skipped:
        logger.info(f"Skipped {skipped} unchanged files")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest product PDFs and property .md files into Firestore vector index"
    )
    parser.add_argument(
        "--bucket",
        default=DEFAULT_BUCKET,
        help=f"GCS bucket name (default: {DEFAULT_BUCKET})",
    )
    parser.add_argument(
        "--collection",
        default=None,
        help="Only ingest files for a specific collection (e.g., 'calden', 'property_1')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and chunk only, skip Firestore writes",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing chunks before ingesting",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest all files even if unchanged",
    )
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
