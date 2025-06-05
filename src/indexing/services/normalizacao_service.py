import ast

REQUIRED_FIELDS = ["title", "brand", "category", "price", "url"]

def aplicar_normalizacao(produto: dict) -> dict:
    novo_produto = produto.copy()

    # 🔁 Garante todos os campos obrigatórios
    for campo in REQUIRED_FIELDS:
        if campo not in novo_produto:
            novo_produto[campo] = ""

    if "images" not in novo_produto or not novo_produto["images"]:
        novo_produto["images"] = []

    elif isinstance(novo_produto["images"], str):
        try:
            novo_produto["images"] = ast.literal_eval(novo_produto["images"])
        except Exception as e:
            print(f"⚠️ Erro ao normalizar imagens: {novo_produto['images']} -> {e}")
            novo_produto["images"] = []

    if not isinstance(novo_produto["images"], list):
        novo_produto["images"] = [str(novo_produto["images"])]

    return novo_produto

def normalizar_dataset(dataset: list[dict]) -> list[dict]:
    return [aplicar_normalizacao(p) for p in dataset if isinstance(p, dict)]
