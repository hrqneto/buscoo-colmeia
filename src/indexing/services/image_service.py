import os
from PIL import Image
from io import BytesIO
import httpx
import boto3

# 🔧 CONFIGURAÇÕES
BUCKET_NAME = "buscaflex-thumbs"
REGIAO = "auto"
ENDPOINT_URL = "https://a2cadc9639c11816e7afa11db881dddf.r2.cloudflarestorage.com"

ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
SECRET_KEY = os.getenv("R2_SECRET_KEY")

# 🌩️ Cliente R2 (S3 compatível)
s3 = boto3.client(
    "s3",
    region_name=REGIAO,
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

# 🖼️ Processa imagem da URL, redimensiona e envia pro R2 — tudo em memória
async def processar_e_enviar_imagem(url_original: str, uuid: str, tamanho=(700, 700)) -> str:
    try:
        print(f"📥 Baixando imagem: {url_original}")
        
        async with httpx.AsyncClient(headers={
            "User-Agent": "Mozilla/5.0"
        }) as client:
            resp = await client.get(url_original, timeout=10)


        if resp.status_code != 200:
            raise Exception("Erro ao baixar imagem")

        print("🔍 Status da imagem:", resp.status_code)
        
        content_type = resp.headers.get("Content-Type", "")
        print("🔍 Content-Type:", resp.headers.get("Content-Type"))
        print(f"🧪 DEBUG: Status code = {resp.status_code}, Content-Type = {content_type}")
        
        if "image" not in content_type:
            raise Exception(f"URL não é uma imagem: {url_original}")

        img = Image.open(BytesIO(resp.content)).convert("RGB")

        # 🛑 Verifica tamanho mínimo antes de redimensionar
        if img.width < 200 or img.height < 200:
            print(f"⚠️ Imagem pequena ({img.width}x{img.height}), mas será usada mesmo assim.")

        img.thumbnail(tamanho)

        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        buffer.seek(0)

        s3.upload_fileobj(
            Fileobj=buffer,
            Bucket=BUCKET_NAME,
            Key=f"products/thumbs/{uuid}.jpg",
            ExtraArgs={"ContentType": "image/jpeg"}
        )

        url_final = f"https://pub-f7ad44c25e7a4c599be0d11851654e0c.r2.dev/products/thumbs/{uuid}.jpg"
        print(f"✅ Upload completo! URL: {url_final}")
        return url_final

    except Exception as e:
        print(f"❌ Erro ao processar imagem ({uuid}): {e}")
        raise

# 🔧 Teste isolado
if __name__ == "__main__":
    import asyncio
    url = "https://rukminim1.flixcart.com/image/300/300/kf75fgw0/cufflink-tie-pin/j/j/v/men-s-silk-necktie-set-with-pocket-square-lapel-pin-and-original-imafvp26zmzkqucy.jpeg"
    uuid = "teste-na-memoria"
    result = asyncio.run(processar_e_enviar_imagem(url, uuid))
    print("🧪 URL final:", result)
