# 🔍 buscoo - backend Python

Este repositório contém o sistema de **indexação vetorial inteligente** do [BuscaFlex](https://buscaflex.ai), responsável por processar catálogos de produtos (via CSV ou URL), gerar **embeddings com IA** e armazená-los no **Qdrant**, além de gerenciar cache, configurações e busca autocompletável.

---

## ⚙️ Requisitos

- Python 3.10+
- Redis local rodando em `localhost:6379`
- Acesso à API do [Qdrant Cloud](https://qdrant.tech/)
- Cloudflare R2 configurado para imagens
- Credencial Firebase (admin SDK JSON)

---

## 🚀 Setup Inicial

### 1️⃣ Criar ambiente virtual

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

### 3️⃣ Rodar localmente com Makefile

```bash
make dev
```

Este comando inicia:
- ✅ API principal (`localhost:8000`)
- 🧠 Microserviço de embedding (`localhost:8001`)

### 4️⃣ Testar no navegador

Documentação interativa:
```
http://localhost:8000/docs
```

---

## 🧠 Como funciona a indexação

O processo completo de ingestão de produtos funciona assim:

1. **Recebimento de arquivo CSV** ou **URL de feed remoto** (CSV/XML).
2. Validação, limpeza e pré-processamento dos dados.
3. Geração de embeddings vetoriais com **IA** via microserviço (`/embed`) utilizando **SentenceTransformer**.
4. Armazenamento dos dados:
   - ✅ **Texto vetorizado** → Qdrant (coleção por cliente)
   - ✅ **Imagens** → Cloudflare R2 (pré-processadas com fallback automático)

> O campo `image` é separado e tratado de forma assíncrona. Caso ausente, tentamos extrair via `<meta property="og:image">` do link do produto.

---

## 📢 Rotas principais

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/upload` | Upload e indexação de arquivo CSV |
| `GET` | `/api/upload-status/{upload_id}` | Retorna status do processamento |
| `POST` | `/api/upload/url` | Indexa catálogo a partir de uma URL (XML ou CSV) |
| `POST` | `/api/upload-cancel/{upload_id}` | Cancela upload em andamento |
| `GET` | `/api/search?q=termo` | Busca textual simples (sem IA) |
| `GET` | `/api/autocomplete?q=termo&client_id=products` | Busca vetorial com autocomplete |
| `DELETE` | `/api/delete-all` | Remove todos os dados do Qdrant e limpa imagens da R2 |
| `POST` | `/api/auth/login` | Autenticação com Firebase via email/senha |
| `GET` | `/api/users/me` | Retorna dados do usuário autenticado |
| `GET` | `/api/admin/configs` | Busca as configurações do cliente autenticado |
| `POST` | `/api/admin/save-configs` | Salva configurações personalizadas no Firestore |

---

## 🧠 Como funciona o autocomplete com IA

O endpoint `/api/autocomplete` realiza uma busca vetorial e preditiva com as seguintes etapas:

- ✨ **Verificação de ruído e entropia** da query para ignorar entradas ruins (ex: spam, termos sem sentido).
- ⚖️ **Vetorizacão semântica** da query com modelo **SentenceTransformer** via microserviço de embedding (`/embed`).
- 🔎 **Busca aproximada em Qdrant** usando HNSW + `score_threshold` dinâmico conforme o tamanho da query.
- 📷 **Extração paralela de imagens** para completar produtos com `image` ausente.
- ⌛ **Cache inteligente em Redis**, com fallback por similaridade em queries semelhantes.

Resultado:
- `products`: produtos relevantes
- `brands`: marcas mais prováveis
- `catalogues`: categorias associadas
- `suggestionsFound`: indica se houve retorno

---

## 🧰 Microserviço de Embedding (IA)

Iniciado automaticamente no `make dev`. Pode ser executado sozinho:

```bash
uvicorn src.services.embedding_microservice:app --reload --port 8001
```

### Rota:
```http
POST /embed
{
  "texts": ["calça jeans masculina"]
}
```

Retorna:
```json
{
  "vectors": [[0.121, -0.055, ...]]
}
```

---

## ☁️ Armazenamento em camadas

- **Qdrant**: texto vetorizado por `client_id`
- **Cloudflare R2**: imagens de produtos
- **Redis**: cache para sugestões, fallback e controle de erros

---

## 🔐 Autenticação Firebase + Firestore

- ✉️ Rota `/api/auth/login` realiza login com email/senha e retorna JWT.
- As rotas protegidas (`/users/me`, `/admin/configs`, `/admin/save-configs`) exigem `Authorization: Bearer <token>`.
- As configurações dos clientes são armazenadas por `clientId` na coleção `configs` do Firestore.

---

## 🚜 Reset total da base

```http
DELETE /api/delete-all
```

- Apaga coleção do Qdrant (produtos)
- Limpa imagens do bucket R2

---

## 📦 Estrutura resumida

```
buscaflex-indexador/
├── main.py                    # Entrypoint FastAPI
├── Makefile                  # Scripts prontos p/ desenvolvimento
├── requirements.txt          # Dependências
├── secrets/firebase-admin.json
├── src/
│   ├── routes/               # Todas as rotas (upload, search, auth)
│   ├── services/             # Indexação, busca, embedding
│   ├── utils/                # Redis, validações, embedding client
│   └── schemas/              # Pydantic models (validação)
```

---

## ❓ Erros comuns

| Erro | Causa | Solução |
|------|-------|---------|
| `Connection refused` | Redis ou microserviço não iniciado | Rode `make dev` |
| `Erro no autocomplete` | Query ruidosa ou baixa entropia | Verifique logs no backend |
| `Query sem sugestões` | Nenhum produto relevante | Tente outro termo |

---
sistema completo de indexação com IA, cache inteligente, API estruturada e pronto para servir autocompletes e buscas em escala! 🚀
