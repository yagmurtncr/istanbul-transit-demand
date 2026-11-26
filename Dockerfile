# Interactive dashboard: day-ahead hourly forecasts for Istanbul public transport.
#   docker run -p 8501:8501 ghcr.io/yagmurtncr/istanbul-transit-demand:latest   ->  http://localhost:8501
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[app]"
COPY app ./app
COPY data/aggregated ./data/aggregated
EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
