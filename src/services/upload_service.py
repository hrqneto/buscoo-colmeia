import os
import pandas as pd
from uuid import uuid4
from fastapi import UploadFile
from src.services.indexing import index_products

async def process_and_index_csv(file: UploadFile):
    """Recebe um arquivo CSV, processa e indexa os produtos."""
    try:
        # Cria um nome de arquivo temporário
        file_path = f"temp_{uuid4()}.csv"
        
        # Salva o arquivo temporariamente
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Lê o arquivo CSV
        df = pd.read_csv(file_path)

        # Remove o arquivo temporário após leitura
        os.remove(file_path)

        # 🔥 Garantir que as colunas estejam corretas
        df = df.rename(columns={"Título": "title", "Descrição": "description", "Marca": "brand", "Preço": "price"})

        # Converte os dados e indexa no Weaviate
        response = await index_products(df.to_dict(orient="records"))

        return {"message": "Arquivo processado e indexado com sucesso!", "details": response}
    
    except Exception as e:
        print(f"❌ Erro ao processar o CSV: {e}")
        return {"error": str(e)}
