"""
Representação vetorial de textos jurídicos (embeddings leves).

Cada documento é convertido em um vetor denso de dimensão fixa por
*feature hashing* ponderado por TF-IDF incremental — a mesma ideia que
permite a um LLM comparar significados: textos semelhantes ficam
próximos no espaço vetorial, e a similaridade de cosseno funciona como
o mecanismo de atenção da memória.

Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

DIMENSAO = 256

# Palavras funcionais do português que não carregam significado jurídico.
_STOPWORDS = {
    "a", "o", "e", "de", "da", "do", "das", "dos", "em", "no", "na",
    "nos", "nas", "um", "uma", "uns", "umas", "para", "por", "com",
    "sem", "sob", "sobre", "que", "se", "ao", "aos", "as", "os", "ou",
    "como", "mais", "mas", "foi", "ser", "ter", "sua", "seu", "suas",
    "seus", "este", "esta", "esse", "essa", "isso", "isto", "aquele",
    "aquela", "pelo", "pela", "pelos", "pelas", "entre", "quando",
    "onde", "qual", "quais", "nao", "não", "sim", "ja", "já", "ate",
    "até", "apos", "após", "desde", "durante", "mediante", "perante",
}


def normalizar(texto: str) -> str:
    """Remove acentos e reduz o texto a minúsculas."""
    nfkd = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def tokenizar(texto: str) -> list[str]:
    """Extrai tokens relevantes (palavras com 3+ letras, fora das stopwords)."""
    palavras = re.findall(r"[a-zà-ú]{3,}", texto.lower())
    return [normalizar(p) for p in palavras if normalizar(p) not in _STOPWORDS]


def _indice_hash(token: str) -> tuple[int, int]:
    """Mapeia um token para (índice, sinal) de forma determinística."""
    digest = hashlib.sha1(token.encode("utf-8")).digest()
    indice = int.from_bytes(digest[:4], "big") % DIMENSAO
    sinal = 1 if digest[4] % 2 == 0 else -1
    return indice, sinal


def vetorizar(texto: str, idf: dict[str, float] | None = None) -> list[float]:
    """
    Converte um texto em vetor de dimensão fixa.

    `idf` é o dicionário de frequências inversas aprendido pela memória
    de longo prazo; quando presente, termos raros (mais informativos)
    pesam mais — o vetor melhora à medida que a IA lê mais processos.
    """
    tokens = tokenizar(texto)
    if not tokens:
        return [0.0] * DIMENSAO

    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    vetor = [0.0] * DIMENSAO
    for token, freq in tf.items():
        peso = 1.0 + math.log(freq)
        if idf:
            peso *= idf.get(token, 1.0)
        indice, sinal = _indice_hash(token)
        vetor[indice] += sinal * peso

    norma = math.sqrt(sum(v * v for v in vetor))
    if norma > 0:
        vetor = [v / norma for v in vetor]
    return vetor


def similaridade(a: list[float], b: list[float]) -> float:
    """Similaridade de cosseno entre dois vetores normalizados."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))
