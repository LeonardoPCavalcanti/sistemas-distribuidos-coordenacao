FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Garantia: se não tiver "bully" no app.py copiado pra imagem, o build falha
RUN grep -n "bully" app.py || (echo "Rotas bully NÃO encontradas no app.py" && exit 1)

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
