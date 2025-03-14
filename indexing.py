import uuid
import asyncio
from weaviate_client import client
from config import PRODUCT_CLASS
from typing import List, Dict

async def loading_animation():
    """Animação de loading durante a indexação."""
    symbols = ["|", "/", "-", "\\"]
    for _ in range(10):
        for symbol in symbols:
            print(f"\r⏳ Indexando produtos... {symbol}", end="", flush=True)
            await asyncio.sleep(0.1)
    print("\r✅ Indexação concluída!\n")

async def index_products(products: List[Dict[str, any]]):
    """Indexa produtos no Weaviate corretamente."""
    try:
        collection = client.collections.get(PRODUCT_CLASS)
        batch_size = 50

        print("\n🚀 Iniciando indexação...\n")
        await loading_animation()

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            formatted_batch = []

            for p in batch:
                obj_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, p["title"]))
                
                formatted_batch.append({
                    "uuid": obj_uuid,  # UUID deve ser passado fora das propriedades
                    "properties": {  # Somente as propriedades definidas no schema
                        "title": p.get("title", "Sem título"),
                        "description": p.get("description", "Sem descrição"),
                        "price": p.get("price", 0.0),
                        "brand": p.get("brand", "Desconhecida")
                    }
                })

            try:
                collection.data.insert_many(formatted_batch)
                print(f"✅ {len(batch)} produtos indexados...")
            except Exception as e:
                print(f"❌ Erro ao indexar lote: {e}")

        return {"message": "✅ CSV processado!", "total_adicionados": len(products)}

    except Exception as e:
        raise RuntimeError(f"❌ Erro ao indexar produtos: {e}")