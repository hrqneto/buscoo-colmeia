import httpx

async def encode_text(text: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.post(
                "http://localhost:8001/embed",
                json={"texts": [text]}
            )
            resp.raise_for_status()
            return resp.json()["vectors"][0]
    except Exception as e:
        raise RuntimeError(f"Erro ao chamar microserviço de embedding: {e}")
