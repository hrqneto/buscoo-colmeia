# Campos obrigatórios
REQUIRED_FIELDS = [
    "title",
    "brand",
    "category",
    "price",
    "url"
]

# Campos opcionais
OPTIONAL_FIELDS = [
    "description",
    "images",
    "composition",
    "uses",
    "side_effects",
    "review_positive",
    "review_average",
    "review_negative"
]

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Dicionário de aliases para mapeamento inteligente
COLUMN_ALIASES = {
    "title": ["product_name", "title", "product_title", "name"],
    "price": ["final_price", "price", "selling_price", "valor"],
    "images": ["image_urls", "main_image", "images", "img"],
    "brand": ["brand", "marca", "manufacturer"],
    "category": ["category", "root_category", "category_name"],
    "url": ["url", "product_url", "link"],
    "description": ["description", "desc", "product_description"],
    "composition": ["composition"],
    "uses": ["uses"],
    "side_effects": ["side_effects"]
}

def detectar_e_mapear_colunas(df):
    df.columns = [col.strip().lower() for col in df.columns]
    original_cols = df.columns.tolist()

    mapeamento = {}

    for campo_padrao, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in original_cols:
                mapeamento[alias] = campo_padrao
                break

    if not all(field in mapeamento.values() for field in REQUIRED_FIELDS):
        return df, f"❌ Mapeamento incompleto. Faltam campos obrigatórios: {[f for f in REQUIRED_FIELDS if f not in mapeamento.values()]}"

    print(f"✅ Mapeamento automático aplicado: {mapeamento}")
    df = df.rename(columns=mapeamento)
    return df, None
