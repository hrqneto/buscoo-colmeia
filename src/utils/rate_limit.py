
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
import time

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 5, window_seconds: int = 1):
        super().__init__(app)
        self.max_requests = max_requests
        self.window = window_seconds
        self.clients = {}

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = time.time()
        request_times = self.clients.get(client_ip, [])

        # Remove requisições antigas fora da janela
        request_times = [t for t in request_times if now - t < self.window]

        if len(request_times) >= self.max_requests:
            return Response(
                content="⚠️ Muitos requests. tente novamente depois.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        request_times.append(now)
        self.clients[client_ip] = request_times
        response = await call_next(request)
        return response
