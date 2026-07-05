"""

Neurology RAG Retriever.
 
Retrieves relevant Neurology knowledge using PGVector.

"""
 
from __future__ import annotations
 
import logging
 
from backend.neurology.config import settings

from backend.neurology.db.pgvector import search_knowledge

from backend.neurology.llm import embedding_client
 
logger = logging.getLogger(__name__)
 
 
class Retriever:

    """

    Retrieves Neurology knowledge from the vector database.

    """
 
    def retrieve(

        self,

        query: str,

        top_k: int | None = None,

        min_similarity: float = 0.40,

    ) -> list[dict]:

        """

        Retrieve the most relevant knowledge chunks.

        """
 
        if top_k is None:

            top_k = settings.top_k
 
        logger.info(

            "Searching Neurology knowledge for: %s",

            query,

        )
 
        embedding = embedding_client.embed_query(query)
 
        results = search_knowledge(

            department="neurology",

            embedding=embedding,

            top_k=top_k,

            min_similarity=min_similarity,

        )
 
        logger.info(

            "Retrieved %d chunks.",

            len(results),

        )
 
        return results
 
    def retrieve_context(

        self,

        query: str,

        top_k: int | None = None,

    ) -> str:

        """

        Convert retrieved chunks into a single context string.

        """
 
        chunks = self.retrieve(

            query=query,

            top_k=top_k,

        )
 
        if not chunks:

            return ""
 
        context = []
 
        for chunk in chunks:
 
            source = chunk.get("source", "Unknown")
 
            page = chunk.get("page", "?")
 
            similarity = chunk.get("similarity", 0.0)
 
            content = chunk.get("content", "")
 
            context.append(

                f"[Source: {source}, Page: {page}, Score: {similarity:.2f}]\n{content}"

            )
 
        return "\n\n".join(context)
 
 
retriever = Retriever()
 
