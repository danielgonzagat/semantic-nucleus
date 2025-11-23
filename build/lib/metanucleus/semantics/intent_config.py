"""
Vocabulário determinístico para intents básicas reconhecidas pelo Metanúcleo.
"""

from __future__ import annotations

from typing import Dict, List

INTENT_KEYWORDS: Dict[str, Dict[str, List[str]]] = {
    "pt": {
        "question": [
            "por que",
            "como",
        ],
        "greeting": [
            "oi",
            "olá",
        ],
    },
    "en": {
        "question": [
            "why",
            "how",
        ],
        "greeting": [
            "hi",
            "hello",
        ],
    },
}

__all__ = ["INTENT_KEYWORDS"]
