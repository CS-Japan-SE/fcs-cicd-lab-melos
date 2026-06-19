FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} \
    $([ -n "$PIP_TRUSTED_HOST" ] && echo "--trusted-host $PIP_TRUSTED_HOST") \
    -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
