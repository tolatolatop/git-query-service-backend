# 构建阶段
FROM python:3.12-slim as builder

# 安装编译依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libgit2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制项目文件
COPY setup.py .
COPY git_query ./git_query

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -e .

# 最终运行阶段
FROM python:3.12-slim

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libgit2-28 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --from=builder /app /app

# 暴露服务端口
EXPOSE 8000

# 启动服务
CMD ["uvicorn", "git_query.api:app", "--host", "0.0.0.0", "--port", "8000"] 