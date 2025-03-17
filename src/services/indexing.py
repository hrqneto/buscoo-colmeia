import uuid
import asyncio
from src.services.weaviate_client import create_weaviate_client
from src.config import PRODUCT_CLASS
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
    """Indexa produtos no Weaviate garantindo que todas as propriedades sejam corretamente salvas."""
    client = None
    try:
        client = create_weaviate_client()
        collection = client.collections.get(PRODUCT_CLASS)
        batch_size = 50

        print("\n🚀 Iniciando indexação...\n")
        await loading_animation()

        total_indexados = 0
        total_atualizados = 0
        total_ignorados = 0

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            formatted_batch = []
            uuids = []

            for p in batch:
                title = str(p.get("title", "")).strip()
                description = str(p.get("description", "")).strip()
                brand = str(p.get("brand", "")).strip()
                category = str(p.get("category", "")).strip()
                specs = str(p.get("specs", "")).strip()
                price = float(p.get("price", 0.0))

                # Verifica se o título é válido
                if not title:
                    print(f"⚠️ Produto ignorado: Sem título válido -> {p}")
                    total_ignorados += 1
                    continue

                # Gera um UUID único para cada produto
                obj_uuid = str(uuid.uuid4())  # UUID aleatório
                uuids.append(obj_uuid)

                # 🔥 Corrigindo a estrutura do JSON enviado ao Weaviate
                formatted_batch.append({
                    "uuid": obj_uuid,
                    "title": title,
                    "description": description if description else "Sem descrição",
                    "brand": brand if brand else "Desconhecida",
                    "category": category if category else "Sem categoria",
                    "specs": specs if specs else "Sem especificações",
                    "price": price
                })

            # Verifica quais produtos já existem
            existing_products = collection.query.fetch_objects_by_ids(uuids)
            existing_uuids = {obj.uuid for obj in existing_products.objects} if existing_products.objects else set()

            insert_batch = []
            for product in formatted_batch:
                if product["uuid"] in existing_uuids:
                    print(f"🔄 Atualizando: {product}")
                    collection.data.update(uuid=product["uuid"], **product)
                    total_atualizados += 1
                else:
                    insert_batch.append(product)

            # Insere os novos produtos
            if insert_batch:
                collection.data.insert_many(insert_batch)
                total_indexados += len(insert_batch)
                print(f"✅ {len(insert_batch)} produtos novos indexados...")

        print(f"\n🚀 Indexação finalizada. Total: {total_indexados} novos, {total_atualizados} atualizados, {total_ignorados} ignorados.")

        return {
            "message": "✅ CSV processado!",
            "total_adicionados": total_indexados,
            "total_atualizados": total_atualizados,
            "total_ignorados": total_ignorados
        }

    except Exception as e:
        print(f"❌ Erro ao indexar produtos: {e}")
        return {"error": str(e)}
    finally:
        if client:
            client.close()
