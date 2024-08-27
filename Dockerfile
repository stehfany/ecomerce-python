# Use uma imagem base do Python
FROM python:3.10-slim

# Instale dependências do sistema necessárias para compilar algumas bibliotecas
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Defina o diretório de trabalho na imagem do Docker
WORKDIR /app

# Copie o arquivo requirements.txt para o diretório de trabalho
COPY requirements.txt .

# Instale as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copie todo o código da aplicação para o diretório de trabalho
COPY . .

# Defina a variável de ambiente para dizer ao Flask qual arquivo executar
ENV FLASK_APP=app.py

# Defina a variável de ambiente para o Flask rodar em modo de produção
ENV FLASK_ENV=production

# Exponha a porta em que o Flask estará escutando
EXPOSE 5000

# Comando para rodar a aplicação Flask
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
