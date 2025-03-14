from weaviate_client import client  # Certifique-se de que esta linha existe
from fastapi import APIRouter, HTTPException, UploadFile, File
import pandas as pd
import os
from uuid import uuid4
from data_processing import clean_and_prepare_data
from indexing import index_products
from weaviate_client import client
from config import PRODUCT_CLASS  # Certifique-se de importar a constante correta
import json

router = APIRouter()

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Recebe um arquivo CSV e o processa para indexação no Weaviate."""
    try:
        file_path = f"temp_{uuid4()}.csv"
        
        with open(file_path, "wb") as f:
            f.write(await file.read())

        df = pd.read_csv(file_path)
        os.remove(file_path)

        df = clean_and_prepare_data(df)
        response = await index_products(df.to_dict(orient="records"))

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
def search_products(query: str):
    """Realiza uma busca híbrida no Weaviate e retorna apenas os produtos relevantes."""
    try:
        print(f"🔍 Buscando: {query}")

        # 🔗 Recuperar a coleção do Weaviate
        collection = client.collections.get(PRODUCT_CLASS)

        # 🔍 Realizar busca híbrida (BM25 + vetorial)
        result = collection.query.hybrid(
            query=query,
            alpha=0.75,
            limit=10,
            return_properties=["title", "description", "price", "brand"]
        )

        # Se não houver resultados, retorna mensagem informativa
        if not result or not hasattr(result, "objects") or not isinstance(result.objects, list):
            return {"message": "Nenhum resultado encontrado"}

        produtos = []

        for obj in result.objects:
            obj_uuid = obj.uuid  # Pega o UUID do objeto

            # Se não tiver UUID, pula
            if not obj_uuid:
                print("⚠️ UUID do objeto é inválido. Pulando...")
                continue

            # 🔍 Buscar detalhes do objeto, excluindo o vetor
            detailed_obj = collection.query.fetch_object_by_id(
                uuid=obj_uuid,
                return_properties=["title", "description", "price", "brand"],
                include_vector=False  # 🚀 REMOVER VETORES
            )

            # Se detailed_obj for vazio, pular esse item
            if not detailed_obj:
                print(f"⚠️ Nenhum objeto encontrado para UUID: {obj_uuid}")
                continue

            # Construir resposta final apenas com as informações desejadas
            produtos.append({
                "uuid": str(obj_uuid),
                "title": detailed_obj.properties.get("title", "Sem título"),
                "description": detailed_obj.properties.get("description", "Sem descrição"),
                "brand": detailed_obj.properties.get("brand", "Desconhecida"),
                "price": detailed_obj.properties.get("price", 0.0)
            })

        # Ordenar por relevância (se disponível)
        produtos = sorted(produtos, key=lambda x: x.get("score", 0), reverse=True)

        print(f"✅ Produtos retornados: {json.dumps(produtos, indent=2, ensure_ascii=False)}")  # Melhor visualização no console
        return produtos

    except Exception as e:
        print(f"❌ Erro ao buscar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
