# BFT WIN — Interface Web (Trading Desk)
# Servidor HTTP puro em Python que expõe o motor do BFT WIN na porta 8765.
FROM python:3.14-slim

# Evita a geração de bytecode e mantém a saída do Python sem buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copia apenas o necessário: a interface web e o motor compartilhado (core/).
# A interface web insere "core" no sys.path em tempo de execução.
COPY web/requirements-container.txt ./web/requirements-container.txt
COPY web/interface_tempo_real.py ./web/interface_tempo_real.py
COPY web/api_captura_otc.py ./web/api_captura_otc.py
COPY core/ ./core/

RUN pip install --no-cache-dir -r web/requirements-container.txt

# Porta do Trading Desk web.
EXPOSE 8765

# O servidor escuta em 0.0.0.0 para ser acessível de fora do container.
CMD ["python", "web/interface_tempo_real.py"]
