import logging
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

async def error_handler(request: Request, exc: Exception):
    """Gestionnaire d'erreurs global"""
    
    if isinstance(exc, HTTPException):
        # Erreurs HTTP explicites (400, 401, 403, 404, etc.)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    elif isinstance(exc, RequestValidationError):
        # Erreurs de validation des données (422)
        logger.warning(f"Validation error: {exc}")
        return JSONResponse(
            status_code=422,
            content={
                "error": True,
                "message": "Données invalides",
                "details": exc.errors(),
                "status_code": 422
            }
        )
    
    elif isinstance(exc, StarletteHTTPException):
        # Autres erreurs HTTP
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": True,
                "message": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    else:
        # Erreurs internes non gérées (500)
        logger.error(f"Internal server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Erreur interne du serveur",
                "status_code": 500
            }
        )

def setup_error_handlers(app):
    """Configure les gestionnaires d'erreurs pour l'application"""
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return await error_handler(request, exc)
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return await error_handler(request, exc)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return await error_handler(request, exc) 