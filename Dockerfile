# Utilise une image officielle Python
FROM python:3.10-slim

WORKDIR /app

# Copier les fichiers nécessaires
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copier le reste du code dans le conteneur
COPY . .

# Exposer le port utilisé par Fast
EXPOSE 8000

# Commande pour lancer l'application
CMD ["python", "api_server.py"]
