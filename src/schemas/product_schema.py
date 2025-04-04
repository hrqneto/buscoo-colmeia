# src/schemas/product_schema.py

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

# Todos os campos esperados
ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

# Função de mapeamento inteligente
def detectar_e_mapear_colunas(df):
    # Normaliza colunas para comparar de forma segura
    df.columns = [col.strip().lower() for col in df.columns]

    mapeamentos_possiveis = [
        {
            'medicine name': 'title',
            'image url': 'url',
            'manufacturer': 'brand',
            'composition': 'composition',
            'uses': 'uses',
            'side_effects': 'side_effects'
        },
        {
            'title': 'title',
            'images': 'images',
            'selling_price': 'price',
            'brand': 'brand',
            'category': 'category',
            'url': 'url'
        }
    ]

    for mapping in mapeamentos_possiveis:
        if all(col in df.columns for col in mapping):
            print(f"✅ Mapeamento automático encontrado com colunas: {list(mapping.keys())}")
            return df.rename(columns=mapping), None

    return df, "❌ Nenhum mapeamento conhecido aplicável ao CSV."
