import boto3
import os
from dotenv import load_dotenv

load_dotenv()

# Configs
BUCKET_NAME = "buscaflex-thumbs"
ENDPOINT_URL = "https://a2cadc9639c11816e7afa11db881dddf.r2.cloudflarestorage.com"
ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
SECRET_KEY = os.getenv("R2_SECRET_KEY")

# Cliente R2
s3 = boto3.client(
    "s3",
    region_name="auto",
    endpoint_url=ENDPOINT_URL,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

# Confirmação antes de apagar tudo
confirm = input(f"⚠️ Isso vai apagar TODOS os arquivos do bucket '{BUCKET_NAME}'. Tem certeza? (s/n): ")
if confirm.strip().lower() != "s":
    print("❎ Cancelado.")
    exit()

# Lista e apaga todos os objetos
response = s3.list_objects_v2(Bucket=BUCKET_NAME)
if "Contents" in response:
    for obj in response["Contents"]:
        print(f"❌ Deletando: {obj['Key']}")
        s3.delete_object(Bucket=BUCKET_NAME, Key=obj["Key"])
    print("✅ Todos os objetos foram deletados.")
else:
    print("ℹ️ Bucket vazio.")
