"""
Middleware de Rate Limiting
Protege a API contra abuso
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

# Criar limiter
limiter = Limiter(key_func=get_remote_address)


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Handler customizado para erro de rate limit.
    """
    return JSONResponse(
        status_code=429,
        content={
            "error": "too_many_requests",
            "message": "Muitas requisições. Por favor, aguarde um momento e tente novamente.",
            "retry_after": exc.detail
        },
        headers={"Retry-After": str(exc.detail)}
    )
