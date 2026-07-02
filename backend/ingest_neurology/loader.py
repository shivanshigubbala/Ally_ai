"""
loader.py

Purpose:
--------
Load all PDF documents from a folder and extract their text.

Input:
    Folder containing PDF files.

Output:
    List of documents with:
        - source filename
        - extracted text

This module does NOT:
- Chunk text
- Generate embeddings
- Store data in the database
"""

from pathlib import Path

try:
    import fitz  # PyMuPDF
    _HAS_FITZ = True
except ImportError:
    _HAS_FITZ = False

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None


class NeurologyLoader:
    """
    Loads all neurology PDF documents from a directory.
    """

    def __init__(self, documents_folder: str | Path):
        self.documents_folder = Path(documents_folder)

        if not self.documents_folder.exists():
            raise FileNotFoundError(
                f"Folder not found: {self.documents_folder}"
            )

    def _extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from a single PDF.
        """

        if _HAS_FITZ:
            doc = fitz.open(str(pdf_path))
            try:
                pages = []

                for page in doc:
                    text = page.get_text("text") or ""

                    if text.strip():
                        pages.append(text.strip())

                return "\n\n".join(pages)

            finally:
                doc.close()

        if PdfReader is None:
            raise ImportError(
                "Install PyMuPDF or pypdf\n"
                "pip install pymupdf pypdf"
            )

        reader = PdfReader(str(pdf_path))

        pages = []

        for page in reader.pages:
            text = page.extract_text() or ""

            if text.strip():
                pages.append(text.strip())

        return "\n\n".join(pages)

    def load_documents(self):
        """
        Load every PDF inside the folder.

        Returns
        -------
        list[dict]
            [
                {
                    "source": "...pdf",
                    "text": "...extracted text..."
                }
            ]
        """

        documents = []

        pdf_files = sorted(self.documents_folder.glob("*.pdf"))

        if not pdf_files:
            raise FileNotFoundError(
                f"No PDF files found in {self.documents_folder}"
            )

        print(f"\nFound {len(pdf_files)} PDF files.\n")

        for pdf in pdf_files:

            print(f"Loading: {pdf.name}")

            text = self._extract_text(pdf)

            documents.append(
                {
                    "source": pdf.name,
                    "text": text
                }
            )

        print("\nAll PDFs loaded successfully.\n")

        return documents


if __name__ == "__main__":

    loader = NeurologyLoader("documents")

    documents = loader.load_documents()

    print(f"Loaded {len(documents)} documents.\n")

    print(documents[0]["source"])
    print(documents[0]["text"][:500])