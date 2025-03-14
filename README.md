# 📌 Buscaflex Indexador

Este repositório contém a API de indexação para o Buscaflex, responsável por processar e armazenar dados de produtos em um banco de dados vetorial usando Weaviate.

## 🚀 **Configuração do Ambiente**

### **1️⃣ Criar um ambiente virtual**
Para evitar conflitos com pacotes do sistema, é necessário criar um ambiente virtual.

```bash
python3 -m venv venv
```

### **2️⃣ Ativar o ambiente virtual**
Após criar o ambiente virtual, ative-o conforme o seu sistema operacional:

✅ **Linux/macOS (Zsh ou Bash)**:
```bash
source venv/bin/activate
```

✅ **Windows (CMD ou PowerShell)**:
```powershell
venv\Scripts\activate
```

Se ativado corretamente, o terminal mostrará algo assim:
```
(venv) ➜  buscaflex-indexador git:(main) ✗
```

### **3️⃣ Instalar as dependências**

Após ativar o ambiente virtual, instale as dependências necessárias:
```bash
pip install -r requirements.txt
```

---

## 🏗 **Executando a API**

### **1️⃣ Iniciar o servidor localmente**
Depois de configurar o ambiente, execute o seguinte comando para iniciar a API:
```bash
uvicorn main:app --reload
```
Se tudo estiver certo, a API estará rodando em `http://127.0.0.1:8000/` 🚀

### **2️⃣ Testando a API**
Acesse a documentação interativa via Swagger:
```
http://127.0.0.1:8000/docs
```


---

## 📂 **Estrutura do Projeto**

```
buscaflex-indexador/
│── main.py  # Código principal da API
│── products.json  # Dados de teste para indexação
│── upload_csv.py  # Script opcional para importar produtos via CSV
│── requirements.txt  # Lista de dependências do projeto
│── venv/  # Ambiente virtual (não precisa ser commitado)
```

---

## ⚡ **Principais Tecnologias**
- **FastAPI** → Framework para criação de APIs rápidas em Python.
- **Weaviate** → Banco de dados vetorial utilizado para busca inteligente.
- **Uvicorn** → Servidor ASGI para rodar a API FastAPI.
- **Sentence Transformers** → Utilizado para gerar embeddings de produtos.

---

## ❓ **Problemas Comuns e Soluções**

### 🔹 **"command not found: pip" ao tentar instalar dependências**
Se o `pip` não estiver instalado, tente rodar:
```bash
sudo apt install python3-pip
```
Ou utilize:
```bash
python3 -m ensurepip --default-pip
```

### 🔹 **Erro "externally-managed-environment" no Ubuntu/Debian**
Este erro ocorre porque o Python impede instalações globais via `pip`. Para resolver:
1. **Crie um ambiente virtual** (conforme explicado acima).
2. **Ative o ambiente virtual**.
3. **Instale os pacotes dentro do ambiente virtual**.

---

Agora é só seguir os passos e começar a indexação dos produtos! 🔥