"""
ingest_neurology.py

Purpose:
--------
Complete ingestion pipeline for Neurology documents.

Pipeline:
PDFs
    ↓
loader.py
    ↓
chunker.py
    ↓
embedder.py
    ↓
PostgreSQL + pgvector
"""

from ingest_neurology.loader import NeurologyLoader
from ingest_neurology.chunker import chunk_text
from ingest_neurology.embedder import NeurologyEmbedder

from db.pgvector_tracker import (
    init_db,
    insert_knowledge_chunks_dev,
    count_knowledge_chunks_dev,
)

DOCUMENTS_FOLDER = "ingest_neurology/documents"
DEPARTMENT = "Neurology"


def main():

    print("=" * 60)
    print("Neurology Knowledge Ingestion")
    print("=" * 60)

    # Create database tables
    init_db()

    # Load embedding model
    embedder = NeurologyEmbedder()

    # Load PDFs
    loader = NeurologyLoader(DOCUMENTS_FOLDER)
    documents = loader.load_documents()

    total_chunks = 0

    for document in documents:

        source = document["source"]
        text = document["text"]

        print(f"\nProcessing: {source}")

        # Split into chunks
        chunks = chunk_text(text)

        if not chunks:
            print("No chunks generated.")
            continue

        print(f"Generated {len(chunks)} chunks.")

        # Generate embeddings
        embeddings = embedder.generate_embeddings(chunks)

        # Store in PostgreSQL
        inserted = insert_knowledge_chunks_dev(
            department=DEPARTMENT,
            source=source,
            page=1,          # Update later if page numbers are available
            contents=chunks,
            embeddings=embeddings,
        )

        print(f"Inserted {inserted} chunks.")

        total_chunks += inserted

    print("\n" + "=" * 60)
    print("Ingestion Complete")
    print("=" * 60)

    print(f"Department       : {DEPARTMENT}")
    print(f"Total Inserted   : {total_chunks}")
    print(
        f"Database Records : {count_knowledge_chunks_dev(DEPARTMENT)}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()