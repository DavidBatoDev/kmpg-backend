from app.core.config import settings


def create_embedding(text: str) -> list[float]:
    """OpenAI embeddings — implement when document_context is in scope."""
    raise NotImplementedError("Embedding service not implemented yet.")


def get_openai_client():
    from openai import OpenAI

    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return OpenAI(api_key=settings.openai_api_key)
