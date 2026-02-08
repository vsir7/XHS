#!/bin/bash

echo "============================================"
echo "小红书视频口播稿文案提取工具"
echo "============================================"

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python 3，请先安装Python 3.7+"
    exit 1
fi

# 检查是否存在虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source venv/bin/activate

# 升级pip
echo "升级pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install fastapi uvicorn python-multipart requests

# 检查FFmpeg是否安装（可选）
if ! command -v ffmpeg &> /dev/null; then
    echo "警告: 未找到FFmpeg，实际项目中需要安装FFmpeg来处理视频"
    echo "请参考: https://ffmpeg.org/download.html"
fi

# 启动应用
echo "启动应用..."
echo "============================================"
echo "前端界面: http://localhost:8000"
echo "API文档: http://localhost:8000/docs"
echo "============================================"

# 运行FastAPI应用
uvicorn app:app --host 0.0.0.0 --port 8000 --reload