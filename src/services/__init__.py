from .indexing import index_products
from .search_service import search_products
from .upload_service import process_and_index_csv
from .weaviate_client import create_weaviate_client

# Expõe essas funções quando importarem "services"
__all__ = [
    "index_products",
    "search_products",
    "process_and_index_csv",
    "create_weaviate_client"
]
