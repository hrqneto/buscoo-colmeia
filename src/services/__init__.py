from .indexing import index_products
from .search_service import search_products
from .upload_service import process_and_index_csv
from .weaviate_client import create_weaviate_client
from .autocomplete_service import get_autocomplete_suggestions

# Serviços auxiliares (não precisa expor se usados só internamente)
# from .validation_service import validar_produto
# from .image_service import processar_e_enviar_imagem
# from .report_service import salvar_relatorio_erros

__all__ = [
    "index_products",
    "search_products",
    "process_and_index_csv",
    "create_weaviate_client",
    "get_autocomplete_suggestions",
]
