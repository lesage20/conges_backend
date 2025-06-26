import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware pour tracer les requêtes HTTP"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Informations sur la requête
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Traitement de la requête
        response = await call_next(request)
        
        # Calcul du temps de traitement
        process_time = time.time() - start_time
        
        # Log de la requête
        logger.info(
            f"{method} {url} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.3f}s - "
            f"IP: {client_ip} - "
            f"User-Agent: {user_agent}"
        )
        
        # Ajouter le temps de traitement dans les headers de réponse
        response.headers["X-Process-Time"] = str(process_time)
        
        return response 