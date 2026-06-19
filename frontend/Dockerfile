FROM python:3.12-slim
WORKDIR /app
ENV HOSTNAME=melos-frontend
RUN apt-get update && apt-get install -y --no-install-recommends procps ca-certificates && rm -rf /var/lib/apt/lists/*
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=
ARG EXTRA_CA_CERT=
COPY requirements.txt .
RUN if [ -n "$EXTRA_CA_CERT" ]; then \
      echo "$EXTRA_CA_CERT" > /usr/local/share/ca-certificates/extra.crt && update-ca-certificates; \
    fi
RUN pip install --no-cache-dir --index-url ${PIP_INDEX_URL} \
    $([ -n "$PIP_TRUSTED_HOST" ] && echo "--trusted-host $PIP_TRUSTED_HOST") \
    flask==3.0.3 requests==2.32.3
RUN pip install --no-cache-dir crowdstrike-aidr
COPY . .
EXPOSE 5000
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
