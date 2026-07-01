"""
embedder.py

Purpose:
--------
Generate vector embeddings for text chunks using
all-MiniLM-L6-v2.

Input:
    List of text chunks.

Output:
    List of embeddings.

This module does NOT:
- Load PDFs
- Chunk text
- Store embeddings in PostgreSQL
"""

from sentence_transformers import SentenceTransformer


class NeurologyEmbedder:
    """
    Generates embeddings for text chunks.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        print(f"\nLoading embedding model: {model_name}")

        self.model = SentenceTransformer(model_name)

        print("Embedding model loaded.\n")

    def generate_embeddings(
        self,
        chunks: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for all chunks.

        Args:
            chunks: List of chunk strings.

        Returns:
            List of embedding vectors.
        """

        if not chunks:
            return []

        embeddings = self.model.encode(
            chunks,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        return embeddings.tolist()