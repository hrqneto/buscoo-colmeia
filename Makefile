.PHONY: dev stop

dev:
	@echo "🔁 Iniciando FastAPI principal na porta 8000..." 
	@uvicorn main:app --reload --port 8000 & \
	echo "🧠 Iniciando microserviço de embedding na porta 8001..." && \
	uvicorn src.services.embedding_microservice:app --port 8001 --reload

stop:
	@echo "🛑 Encerrando serviços nas portas 8000 e 8001..."
	@lsof -ti :8000 | xargs kill -9 || true
	@lsof -ti :8001 | xargs kill -9 || true
