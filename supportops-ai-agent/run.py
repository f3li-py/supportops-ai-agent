import os
import sys
import webbrowser
import uvicorn
from app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    url = f"http://{settings.host}:{settings.port}"

    print("=" * 60)
    print("🚀 Iniciando SupportOps AI Agent...")
    print(f"🌐 Painel Web:     {url}")
    print(f"📖 Documentação:  {url}/docs")
    print(f"🤖 Modelo Gemini: {settings.gemini_model}")
    print("=" * 60)
    print("Pressione CTRL+C no terminal para parar o servidor.\n")

    # Abre o navegador automaticamente
    try:
        webbrowser.open(url)
    except Exception:
        pass

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
