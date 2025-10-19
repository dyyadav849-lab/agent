from fastapi import APIRouter

from app.auth.modes import SessionAuthMode, get_session_auth_mode
from app.core.config import app_config
from app.routes.doc_kb_route.controller import doc_kb_route
from app.routes.health_check import health_check_router
from app.routes.oidc import oidc_router
from app.routes.s3_route.controller import s3_storage_route
from app.routes.slack_kb_route.controller import slack_kb_route

router = APIRouter()
router.include_router(router=health_check_router, tags=["Health Check"])
router.include_router(router=slack_kb_route, tags=["Slack KB RAG"])
router.include_router(router=doc_kb_route, tags=["Document KB RAG"])
router.include_router(router=s3_storage_route, tags=["S3 Storage"])

# only add OIDC routes for non-proxy mode session use cases
if get_session_auth_mode(app_config.auth_mode) != SessionAuthMode.PROXY:
    router.include_router(router=oidc_router, tags=["OpenID Connect"])
