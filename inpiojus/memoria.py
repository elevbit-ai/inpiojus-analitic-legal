"""
Memória persistente da InpioJus — arquitetura inspirada em LLM.

Três camadas, análogas às de um grande modelo de linguagem:

* **Memória de curto prazo** — janela de contexto: as últimas análises
  ficam integralmente disponíveis para a sessão corrente.
* **Memória de longo prazo** — pesos consolidados: vocabulário jurídico
  aprendido (IDF incremental), entidades recorrentes (partes, varas,
  leis) e estatísticas acumuladas. É o "treinamento contínuo" da IA.
* **Memória episódica** — cada processo analisado vira um episódio com
  embedding próprio; a recuperação por similaridade de cosseno funciona
  como atenção sobre o passado ("já vi um caso parecido com este").

A consolidação (curto prazo → longo prazo) acontece automaticamente,
com decaimento suave dos pesos antigos — a IA esquece devagar o que
deixa de ser relevante e reforça o que reaparece.

Tudo é armazenado em JSON legível em ``~/.inpiojus/memoria`` — o usuário
é dono da própria memória da IA e pode inspecioná-la, copiá-la ou
apagá-la a qualquer momento. Nenhum dado sai da máquina.

Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import json
import math
import os
import time
from pathlib import Path

from . import vetor

JANELA_CURTO_PRAZO = 12       # análises mantidas integralmente em contexto
LIMITE_EPISODIOS = 500        # episódios retidos na memória episódica
FATOR_DECAIMENTO = 0.995      # decaimento dos pesos a cada consolidação


def _diretorio_padrao() -> Path:
    base = os.environ.get("INPIOJUS_MEMORIA")
    if base:
        return Path(base)
    return Path.home() / ".inpiojus" / "memoria"


class Memoria:
    """Gerencia as três camadas de memória da InpioJus."""

    def __init__(self, diretorio: Path | None = None):
        self.dir = Path(diretorio) if diretorio else _diretorio_padrao()
        self.dir.mkdir(parents=True, exist_ok=True)
        self._curto = self._carregar("curto_prazo.json", [])
        self._longo = self._carregar("longo_prazo.json", {
            "vocabulario": {},        # token -> nº de documentos em que apareceu
            "entidades": {},          # categoria -> {valor: contagem}
            "documentos_vistos": 0,
            "criada_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        self._episodica = self._carregar("episodica.json", [])

    # ------------------------------------------------------------------
    # Persistência
    # ------------------------------------------------------------------
    def _carregar(self, nome: str, padrao):
        caminho = self.dir / nome
        if caminho.exists():
            try:
                return json.loads(caminho.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return padrao
        return padrao

    def _salvar(self, nome: str, dados) -> None:
        caminho = self.dir / nome
        caminho.write_text(
            json.dumps(dados, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )

    def gravar(self) -> None:
        self._salvar("curto_prazo.json", self._curto)
        self._salvar("longo_prazo.json", self._longo)
        self._salvar("episodica.json", self._episodica)

    # ------------------------------------------------------------------
    # IDF aprendido — quanto mais processos a IA lê, melhor ela pesa
    # os termos ao vetorizar (aprendizado contínuo).
    # ------------------------------------------------------------------
    def idf(self) -> dict[str, float]:
        n = max(self._longo["documentos_vistos"], 1)
        return {
            token: 1.0 + math.log(n / (1 + freq))
            for token, freq in self._longo["vocabulario"].items()
        }

    # ------------------------------------------------------------------
    # Registro de uma nova análise
    # ------------------------------------------------------------------
    def registrar(self, analise: dict, texto: str) -> None:
        """Grava uma análise nas três camadas e consolida."""
        embedding = vetor.vetorizar(texto, self.idf() or None)

        episodio = {
            "quando": time.strftime("%Y-%m-%d %H:%M:%S"),
            "numero_processo": analise.get("numero_processo"),
            "classe": analise.get("classe"),
            "partes": analise.get("partes"),
            "resumo_curto": analise.get("resumo_curto"),
            "embedding": [round(v, 5) for v in embedding],
        }
        self._episodica.append(episodio)
        if len(self._episodica) > LIMITE_EPISODIOS:
            self._episodica = self._episodica[-LIMITE_EPISODIOS:]

        self._curto.append({
            "quando": episodio["quando"],
            "numero_processo": episodio["numero_processo"],
            "analise": analise,
        })
        if len(self._curto) > JANELA_CURTO_PRAZO:
            self._curto = self._curto[-JANELA_CURTO_PRAZO:]

        self._consolidar(analise, texto)
        self.gravar()

    def _consolidar(self, analise: dict, texto: str) -> None:
        """Curto prazo → longo prazo: reforço com decaimento suave."""
        longo = self._longo

        # Decaimento: o que não reaparece perde peso lentamente.
        longo["vocabulario"] = {
            t: f * FATOR_DECAIMENTO
            for t, f in longo["vocabulario"].items()
            if f * FATOR_DECAIMENTO > 0.05
        }

        for token in set(vetor.tokenizar(texto)):
            longo["vocabulario"][token] = longo["vocabulario"].get(token, 0.0) + 1.0

        entidades = longo["entidades"]
        for categoria, valores in (analise.get("entidades") or {}).items():
            grupo = entidades.setdefault(categoria, {})
            for valor in valores:
                grupo[valor] = grupo.get(valor, 0) + 1

        longo["documentos_vistos"] += 1

    # ------------------------------------------------------------------
    # Recuperação (atenção sobre o passado)
    # ------------------------------------------------------------------
    def similares(self, texto: str, k: int = 5, ignorar_numero: str | None = None) -> list[dict]:
        """Retorna os k episódios mais parecidos com o texto dado."""
        consulta = vetor.vetorizar(texto, self.idf() or None)
        pontuados = []
        for ep in self._episodica:
            if ignorar_numero and ep.get("numero_processo") == ignorar_numero:
                continue
            sim = vetor.similaridade(consulta, ep.get("embedding", []))
            if sim > 0.05:
                pontuados.append((sim, ep))
        pontuados.sort(key=lambda par: par[0], reverse=True)
        return [
            {
                "similaridade": round(sim, 3),
                "quando": ep["quando"],
                "numero_processo": ep.get("numero_processo"),
                "classe": ep.get("classe"),
                "resumo_curto": ep.get("resumo_curto"),
            }
            for sim, ep in pontuados[:k]
        ]

    def buscar(self, termo: str, k: int = 10) -> list[dict]:
        """Busca textual simples sobre a memória episódica."""
        termo_norm = vetor.normalizar(termo)
        achados = []
        for ep in reversed(self._episodica):
            alvo = vetor.normalizar(json.dumps(
                {c: v for c, v in ep.items() if c != "embedding"},
                ensure_ascii=False,
            ))
            if termo_norm in alvo:
                achados.append({
                    "quando": ep["quando"],
                    "numero_processo": ep.get("numero_processo"),
                    "classe": ep.get("classe"),
                    "resumo_curto": ep.get("resumo_curto"),
                })
            if len(achados) >= k:
                break
        return achados

    # ------------------------------------------------------------------
    # Introspecção e manutenção
    # ------------------------------------------------------------------
    def estatisticas(self) -> dict:
        vocab = self._longo["vocabulario"]
        top_termos = sorted(vocab.items(), key=lambda kv: kv[1], reverse=True)[:15]
        entidades = {
            categoria: sorted(valores.items(), key=lambda kv: kv[1], reverse=True)[:5]
            for categoria, valores in self._longo["entidades"].items()
        }
        return {
            "diretorio": str(self.dir),
            "criada_em": self._longo.get("criada_em"),
            "documentos_vistos": self._longo["documentos_vistos"],
            "episodios_retidos": len(self._episodica),
            "janela_curto_prazo": len(self._curto),
            "vocabulario_aprendido": len(vocab),
            "termos_mais_fortes": [t for t, _ in top_termos],
            "entidades_recorrentes": entidades,
        }

    def contexto_recente(self) -> list[dict]:
        return list(self._curto)

    def apagar(self) -> None:
        """Apaga toda a memória (ação irreversível, pedida pelo usuário)."""
        self._curto = []
        self._episodica = []
        self._longo = {
            "vocabulario": {},
            "entidades": {},
            "documentos_vistos": 0,
            "criada_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.gravar()
