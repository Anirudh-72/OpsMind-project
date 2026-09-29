"""OpsMind CLI bootstrapper."""

import sys
import uvicorn
from app.config import settings


def main():
    """Boot the OpsMind development server."""
    print("=" * 60)
    print(" OpsMind — Memory-Aware Incident Response Assistant")
    print("=" * 60)
    print(f" Environment : {settings.OPSMIND_ENV}")
    print(f" Server URL  : http://{settings.HOST}:{settings.PORT}")
    print(
        f" Hindsight   : {'Live Cloud (' + settings.HINDSIGHT_API_URL + ')' if settings.has_hindsight_credentials else '[SIMULATION MODE - No API Key]'}"
    )
    print(
        f" LLM Model   : {settings.GROQ_MODEL if settings.has_llm_credentials else '[FALLBACK REASONER - No Groq Key]'}"
    )
    print("=" * 60)

    import os
    should_reload = "--reload" in sys.argv or os.getenv("OPSMIND_RELOAD", "false").lower() == "true"

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=should_reload,
    )


if __name__ == "__main__":
    main()
