import os
import pandas as pd
from uuid import uuid4
from fastapi import UploadFile
from src.services.indexing import index_products

async def process_and_index_csv(file: UploadFile):
    """Recebe um arquivo CSV, processa e indexa os produtos."""
    file_path = f"temp_{uuid4()}.csv"
    try:
        # Salva arquivo temporário
        with open(file_path, "wb") as f:
            f.write(await file.read())

        # Tenta múltiplos encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path, 
                    encoding=encoding,
                    on_bad_lines='skip',
                    sep=',',
                    engine='python'
                )
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            return {"error": "Falha ao decodificar o arquivo (encoding não reconhecido)"}

        # Verifica se temos as colunas do formato antigo
        if 'title' in df.columns and 'brand' in df.columns:
            # Formato novo já está correto
            pass
        elif '""' in df.columns:  # Se for o formato com coluna vazia no início
            # Mapeamento para o formato do seu output.csv
            column_mapping = {
                'title': 'title',
                'brand': 'brand',
                'category': 'category',
                'images': 'image',
                'url': 'url',
                'selling_price': 'price',
                'description': 'description'
            }
            
            # Renomeia as colunas
            df = df.rename(columns=column_mapping)
            
            # Seleciona apenas as colunas necessárias
            df = df[list(column_mapping.values())]
            
            # Garante que a imagem seja uma string (pega a primeira URL se for múltiplas imagens)
            if 'image' in df.columns:
                df['image'] = df['image'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else '')
        else:
            return {"error": "Formato de CSV não reconhecido"}

        # Conversão segura de preços
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        else:
            df['price'] = 0

        # Preenche valores vazios
        for col in ['description', 'brand', 'category']:
            if col in df.columns:
                df[col] = df[col].fillna('')
            else:
                df[col] = ''

        # Remove linhas com título vazio
        df = df[df['title'].notna() & (df['title'].str.strip() != '')]

        response = await index_products(df.to_dict(orient="records"))
        return {
            "message": "Arquivo processado e indexado com sucesso!",
            "details": response,
            "stats": {
                "total_recebido": len(df),
                "total_indexado": response.get("adicionados", 0)
            }
        }

    except Exception as e:
        print(f"❌ Erro ao processar o CSV: {e}")
        return {"error": f"Erro interno: {str(e)}"}
    finally:
        # Garante que o arquivo temporário será removido
        if os.path.exists(file_path):
            os.remove(file_path)