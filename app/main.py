from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.routers import resume, job, match

app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

# API 路由（必须在 StaticFiles 之前注册）
app.include_router(resume.router, prefix="/api/v1")
app.include_router(job.router, prefix="/api/v1")
app.include_router(match.router, prefix="/api/v1")


@app.get("/api/health")
def health():
    return {"project": settings.PROJECT_NAME, "version": settings.VERSION}


# 生产环境：挂载前端静态文件
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # 静态资源（JS/CSS/图片等）
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")

    # SPA 回退：所有非 API 路由返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        index_path = frontend_dist / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"detail": "Frontend not found"}
else:
    @app.get("/{full_path:path}")
    async def no_frontend(full_path: str):
        return {"detail": "Frontend not built. Run: cd frontend && npm run build"}
