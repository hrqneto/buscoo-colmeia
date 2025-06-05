import pandas as pd

def clean_and_prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Remove valores NaN e formata os dados antes da indexação."""
    print("🛠️ Limpando e formatando os dados...")
    required_columns = ["title", "description", "price", "brand"]
    
    if not all(col in df.columns for col in required_columns):
        raise ValueError("CSV deve conter as colunas: title, description, price, brand")

    df = df[required_columns].where(pd.notna(df), None)
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    
    print("✅ Dados preparados!")
    return df
