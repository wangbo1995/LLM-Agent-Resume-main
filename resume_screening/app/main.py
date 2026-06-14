"""
应用入口点
"""
from dotenv import load_dotenv
load_dotenv()  # 必须在其他 app 导入之前加载 .env

from fastapi import FastAPI
from app.api import routes

app = FastAPI(title="Resume Screener API", description="基于LLM的智能简历筛选系统 API")

# 包含API路由
app.include_router(routes.router)


@app.get("/")
async def root():
    return {"message": "Welcome to the Resume Screener API"}