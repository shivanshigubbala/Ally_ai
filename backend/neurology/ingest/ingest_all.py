"""

Complete Neurology Knowledge Ingestion Pipeline.
 
Pipeline:
 
PDF

    ↓

Extract Text

    ↓

Chunk Text

    ↓

Generate Embeddings

    ↓

Store in PostgreSQL (pgvector)

"""
 
from __future__ import annotations
 
import logging

from pathlib import Path
 
from backend.neurology.ingest.chunker import TextChunker

from backend.neurology.ingest.embed_store import EmbeddingStore

from backend.neurology.ingest.extract_pdf import PDFExtractor
 
logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)
 
 
class NeurologyKnowledgeIngestor:

    """

    Runs the entire knowledge ingestion pipeline.

    """
 
    def __init__(self) -> None:
 
        self.extractor = PDFExtractor()

        self.chunker = TextChunker()

        self.store = EmbeddingStore()
 
    def ingest_directory(

        self,

        knowledge_dir: str | Path,

        clear_existing: bool = False,

    ) -> None:

        """

        Ingest every PDF inside the knowledge directory.

        """
 
        knowledge_dir = Path(knowledge_dir)
 
        if not knowledge_dir.exists():

            raise FileNotFoundError(

                f"Knowledge directory not found: {knowledge_dir}"

            )
 
        pdf_files = sorted(knowledge_dir.glob("*.pdf"))
 
        if not pdf_files:

            logger.warning("No PDF files found.")

            return
 
        logger.info("Found %d PDF files", len(pdf_files))
 
        if clear_existing:

            self.store.clear()
 
        for pdf in pdf_files:
 
            logger.info("=" * 60)

            logger.info("Processing %s", pdf.name)
 
            pages = self.extractor.extract(pdf)
 
            chunks = self.chunker.chunk_document(

                pdf.name,

                pages,

            )
 
            self.store.store_chunks(chunks)
 
            logger.info(

                "%s completed (%d chunks)",

                pdf.name,

                len(chunks),

            )
 
        logger.info("=" * 60)

        logger.info("Knowledge ingestion completed successfully.")
 
 
if __name__ == "__main__":
 
    knowledge_folder = (

        Path(__file__)

        .resolve()

        .parent

        .parent

        / "knowledge"

    )
 
    ingestor = NeurologyKnowledgeIngestor()
 
    ingestor.ingest_directory(

        knowledge_folder,

        clear_existing=False,

    )
 
