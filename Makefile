.PHONY: dev stop

dev:
	@echo "🧹 Limpando portas 8000 e 8001 se estiverem ocupadas..."
	@lsof -ti :8000 | xargs -r kill -9 || true
	@lsof -ti :8001 | xargs -r kill -9 || true
	@echo "🔁 Iniciando FastAPI principal na porta 8000..."
	@uvicorn main:app --reload --port 8000 & \
	echo "🧠 Iniciando microserviço de embedding na porta 8001..." && \
	uvicorn src.microservices.embedding_microservice:app --reload --port 8001

stop:
	@echo "🛑 Encerrando serviços nas portas 8000 e 8001..."
	@lsof -ti :8000 | xargs -r kill -9 || true
	@lsof -ti :8001 | xargs -r kill -9 || true
