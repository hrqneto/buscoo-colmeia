import ast
from typing import Dict, Tuple

def validar_produto(p: Dict[str, any]) -> Tuple[bool, str]:
    title = str(p.get("title", "")).strip()
    url = str(p.get("url", "")).strip()
    images = p.get("images", "[]")

    if not title:
        return False, "Título ausente"
    
    if not url or "http" not in url:
        return False, "URL do produto ausente ou inválida"
    
    try:
        image_list = ast.literal_eval(images)
        if not (isinstance(image_list, list) and image_list and "http" in image_list[0]):
            return False, "Imagem inválida ou ausente"
    except:
        return False, "Erro ao processar campo de imagens"

    return True, "OK"
