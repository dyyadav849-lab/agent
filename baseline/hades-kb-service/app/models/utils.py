from pathlib import Path
from typing import Any, Dict, List

import tiktoken
from requests import RequestException

from app.models.azure_openai_model import get_azure_openai_embeddings_model


def chunk_data(data: str, chunk_size: int = 50) -> List[Dict[str, Any]]:
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(data)
    chunks = []
    for i in range(0, len(tokens), chunk_size):
        chunk_tokens = tokens[i : i + chunk_size]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(
            {"text": chunk_text, "tokens": num_tokens_from_string(chunk_text)}
        )
    return chunks


def read_file(file_path: str) -> str:
    path = Path(file_path)
    if path.is_file() and path.suffix == ".txt":
        return path.read_text(encoding="utf-8")

    err_msg = f"File not found or unsupported file type: {file_path}"
    raise ValueError(err_msg)


# Generate embeddings from text
def generate_embedding(text: str) -> list[float]:
    embedding = get_azure_openai_embeddings_model()
    try:
        response = embedding.embed_query(text)
    except (RequestException, TypeError, ValueError, AttributeError) as e:
        err_msg = f"Failed to generate embeddings: {e}"
        raise ValueError(err_msg) from e  # Exception chaining
    return response


# Calculate number of tokens
def num_tokens_from_string(string: str, encoding_name: str = "cl100k_base") -> int:
    if not string:
        return 0
    # Returns the number of tokens in a text string
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(string))
