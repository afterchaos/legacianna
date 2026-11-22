"""Lista os modelos de chat disponíveis na sua conta da Groq. Rode: python listar_modelos.py"""
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

IGNORAR = ("whisper", "guard", "tts", "orpheus", "safeguard", "compound")

modelos = Groq(api_key=os.getenv("GROQ_API_KEY")).models.list().data
for m in sorted(modelos, key=lambda m: m.id):
    if not any(x in m.id.lower() for x in IGNORAR):
        print(m.id)
print("\nPara trocar, coloque no .env:  GROQ_MODEL=<id do modelo>")
