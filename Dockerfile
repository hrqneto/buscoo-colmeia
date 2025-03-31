# Usa uma imagem oficial do Python
FROM python:3.12

# Define diretório de trabalho
WORKDIR /app

# Copia os arquivos do indexador para dentro do container
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Expõe a porta 8000
EXPOSE 8000

# Comando para rodar o serviço
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
