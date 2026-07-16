FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# static/ est obligatoire : main.py fait StaticFiles(directory=<racine>/static) a l'import,
# donc une image sans lui crashe au demarrage. Le compose le masquait en montant ./backend
# sur /app, ce qui fournissait static/ depuis l'hote : le compose marchait, l'image seule non.
COPY static ./static
RUN mkdir -p /app/data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
