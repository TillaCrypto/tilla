# TILLA MCP server: read-only market data tools over stdio.
# Build: docker build -t tilla-mcp .    Run: docker run -i --rm -e TILLA_API_KEY=tk_live_... tilla-mcp
FROM python:3.12-slim
WORKDIR /app
COPY mcp/ /app/mcp/
RUN pip install --no-cache-dir /app/mcp && useradd --create-home --uid 10001 tilla
USER tilla
ENV TILLA_MCP_TRANSPORT=stdio PYTHONUNBUFFERED=1
ENTRYPOINT ["tilla-mcp"]
