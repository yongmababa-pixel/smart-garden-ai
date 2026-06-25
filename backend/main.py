"""
FastAPI 主入口 —— 路由注册 + CORS + 数据库初始化
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database import init_db
from routers import kb, tasks, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    init_db()
    yield


app = FastAPI(
    title="智慧园林管理系统 API",
    description="Smart Garden Management System — 知识库 / 工单 / 报表 后端服务",
    version="1.0.0",
    lifespan=lifespan,
)

# ─── CORS 配置 ────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 路由注册 ────────────────────────────────────────────

app.include_router(kb.router)
app.include_router(tasks.router)
app.include_router(reports.router)


# ─── 根路径 & 健康检查 ───────────────────────────────────

@app.get("/", tags=["系统"])
def root():
    return {
        "service": "智慧园林管理系统",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health", tags=["系统"])
def health():
    return {"status": "ok"}


# ─── 直接运行入口 ────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
