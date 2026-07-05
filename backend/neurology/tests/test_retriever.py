"""
Unit tests for Neurology Retriever.
"""

from backend.neurology.rag import retriever


def test_retriever_import():
    """Retriever singleton should exist."""

    assert retriever is not None


def test_retrieve_returns_list():
    """retrieve() should return a list."""

    results = retriever.retrieve(
        "What are the symptoms of stroke?"
    )

    assert isinstance(results, list)


def test_retrieve_returns_chunks():
    """retrieve() should return at least one chunk for a known query."""

    results = retriever.retrieve(
        "What are the symptoms of stroke?"
    )

    assert len(results) > 0


def test_retrieve_context_returns_string():
    """retrieve_context() should return formatted context."""

    context = retriever.retrieve_context(
        "What are the symptoms of stroke?"
    )

    assert isinstance(context, str)
    assert len(context) > 0


def test_top_k_limit():
    """Retriever should respect top_k."""

    results = retriever.retrieve(
        "What are the symptoms of stroke?",
        top_k=2,
    )

    assert len(results) <= 2


def test_unknown_query_does_not_crash():
    """Retriever should not crash on unrelated queries."""

    results = retriever.retrieve(
        "banana spaceship galaxy"
    )

    assert isinstance(results, list)


def test_unknown_query_context_returns_string():
    """retrieve_context() should always return a string."""

    context = retriever.retrieve_context(
        "banana spaceship galaxy"
    )

    assert isinstance(context, str)
