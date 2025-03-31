
from sentence_transformers import SentenceTransformer

# Inicializa o modelo uma única vez para uso global
model = SentenceTransformer("all-MiniLM-L6-v2")

def encode_text(text: str) -> list[float]:
    """Transforma texto em vetor (embedding)."""
    return model.encode(text).tolist()
