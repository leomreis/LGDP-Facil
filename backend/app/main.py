from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.companies import router as companies_router
from app.api.onboarding import router as onboarding_router
from app.api.policy_documents import router as policy_documents_router
from app.api.reports import router as reports_router
from app.api.scans import router as scans_router
from app.api.team import router as team_router
from app.api.users import router as users_router
from app.core.config import get_settings
from app.core.database import get_db
from app.core.observability import init_sentry
from app.core.security_headers import SecurityHeadersMiddleware

init_sentry(get_settings())

app = FastAPI(
    title="LGPD Fácil",
    description="API de compliance LGPD para PME",
    version="0.1.0",
)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router)
app.include_router(onboarding_router)
app.include_router(policy_documents_router)
app.include_router(scans_router)
app.include_router(reports_router)
app.include_router(users_router)
app.include_router(team_router)


@app.get("/health", tags=["infra"])
def health_check():
    """Liveness: só confirma que o processo da API está de pé, sem checar
    dependências — é o que um load balancer chama a cada poucos segundos, e
    não deve ficar lento nem falhar por um problema no banco."""
    return {"status": "ok"}


@app.get("/health/ready", tags=["infra"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness: confirma que as dependências que a API precisa para
    responder de verdade estão alcançáveis (banco sempre; Redis só se
    configurada). Separado de /health de propósito — ver docstring acima."""
    settings = get_settings()
    problemas: dict[str, str] = {}

    try:
        db.execute(text("SELECT 1"))
    except Exception as erro:
        problemas["database"] = str(erro)

    if settings.redis_url:
        try:
            from app.core.queue import get_redis_connection

            get_redis_connection().ping()
        except Exception as erro:
            problemas["redis"] = str(erro)

    if problemas:
        return JSONResponse(
            status_code=503, content={"status": "unavailable", "problemas": problemas}
        )
    return {"status": "ok"}
