"""Test rapide de la connexion OpenRouter."""
from src.rag.llm_client import OpenRouterClient

client = OpenRouterClient(model_key="gemma-4-26b")
print(f"Modele: {client.model}")
print("Envoi d'une question test...")

response = client.generate("Dis bonjour en une phrase.", system="Tu es un assistant.")
print(f"Reponse: {response}")
