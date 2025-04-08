import ast
from typing import Dict, Tuple, Any

def validar_produto(p: Dict[str, Any]) -> Tuple[bool, str]:
    title = str(p.get("title", "")).strip()
    url = str(p.get("url", "")).strip()
    images_raw = p.get("images", [])

    # 🧪 Validação do título
    if not title:
        return False, "Título ausente"
    
    # 🧪 Validação da URL
    if not url or "http" not in url:
        return False, "URL do produto ausente ou inválida"
    
    # 🧪 Validação da imagem
    try:
        if isinstance(images_raw, list):
            image_list = images_raw
        elif isinstance(images_raw, str):
            image_list = ast.literal_eval(images_raw)
        else:
            print(f"❌ Tipo inesperado em 'images': {type(images_raw)} -> {images_raw}")
            return False, "Campo de imagens com tipo inválido"

        if not isinstance(image_list, list) or not image_list:
            return False, "Lista de imagens ausente ou vazia"

        first_img = str(image_list[0]).strip()
        if not first_img or "http" not in first_img:
            print(f"❌ Primeira imagem inválida: {first_img}")
            return False, "Imagem inválida ou ausente"

    except Exception as e:
        print(f"❌ Erro ao processar campo de imagens: {images_raw} -> {e}")
        return False, "Erro ao processar campo de imagens"

    return True, "OK"
