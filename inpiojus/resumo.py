"""
Gerador de resumos da InpioJus.

Transforma a análise estruturada em um resumo claro, em português,
pronto para leitura por advogados, partes ou estudantes. Quando a
memória da IA conhece casos semelhantes, o resumo ganha uma seção de
insights comparativos — é a memória trabalhando a favor da clareza.

Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

LINHA = "─" * 62


def _secao(titulo: str) -> str:
    return f"\n{titulo}\n{LINHA}"


def _lista(itens: list[str], vazio: str = "  (não identificado nos autos)") -> str:
    if not itens:
        return vazio
    return "\n".join(f"  • {item}" for item in itens)


def gerar(analise: dict, similares: list[dict] | None = None,
          memoria_stats: dict | None = None, completo: bool = True) -> str:
    """Gera o resumo textual do processo."""
    a = analise
    partes_ativo = ", ".join(a["polo_ativo"]) or "não identificado"
    partes_passivo = ", ".join(a["polo_passivo"]) or "não identificado"

    saida: list[str] = []
    saida.append("╔" + "═" * 60 + "╗")
    saida.append("║  InpioJus Analitic Legal — Resumo Inteligente do Processo  ║".center(62))
    saida.append("╚" + "═" * 60 + "╝")

    saida.append(_secao("IDENTIFICAÇÃO"))
    saida.append(f"  Processo nº ...: {a['numero_processo']}")
    saida.append(f"  Classe ........: {a['classe']}")
    saida.append(f"  Fase atual ....: {a['fase']}")
    if a["juizo"]:
        saida.append(f"  Juízo .........: {a['juizo'][0]}")
    if a["tribunal"]:
        saida.append(f"  Tribunal ......: {a['tribunal'][0]}")

    saida.append(_secao("PARTES"))
    saida.append(f"  Polo ativo ....: {partes_ativo}")
    saida.append(f"  Polo passivo ..: {partes_passivo}")
    outros = {
        papel: nomes for papel, nomes in a["partes"].items()
        if not any(n in a["polo_ativo"] + a["polo_passivo"] for n in nomes)
    }
    for papel, nomes in outros.items():
        saida.append(f"  {papel.capitalize():<15}: {', '.join(nomes)}")

    if completo:
        saida.append(_secao("FUNDAMENTOS LEGAIS CITADOS"))
        saida.append(_lista(a["fundamentos_legais"]))
        if a["artigos_citados"]:
            saida.append("\n  Artigos:")
            saida.append(_lista(a["artigos_citados"]))

        if a["pedidos"]:
            saida.append(_secao("PEDIDOS IDENTIFICADOS"))
            saida.append(_lista(a["pedidos"]))

    if a["decisoes"]:
        saida.append(_secao("DECISÕES E COMANDOS JUDICIAIS"))
        saida.append(_lista(a["decisoes"]))

    if a["valores"]:
        saida.append(_secao("VALORES ENVOLVIDOS"))
        saida.append(_lista(a["valores"]))

    if completo and a["prazos"]:
        saida.append(_secao("PRAZOS DETECTADOS"))
        saida.append(_lista(a["prazos"]))

    if completo and a["datas_relevantes"]:
        saida.append(_secao("DATAS RELEVANTES"))
        saida.append("  " + " | ".join(a["datas_relevantes"][:8]))

    saida.append(_secao("SÍNTESE"))
    saida.append(_sintese(a))

    if similares:
        saida.append(_secao("MEMÓRIA DA IA — CASOS SEMELHANTES JÁ ANALISADOS"))
        for s in similares:
            saida.append(
                f"  • [{int(s['similaridade'] * 100)}% similar] "
                f"{s.get('resumo_curto') or s.get('numero_processo')} "
                f"(analisado em {s['quando']})"
            )

    if memoria_stats:
        saida.append(
            f"\n  Memória: {memoria_stats['documentos_vistos']} processos aprendidos · "
            f"{memoria_stats['vocabulario_aprendido']} termos no vocabulário jurídico."
        )

    saida.append("\n" + LINHA)
    saida.append("  Gerado por InpioJus Analitic Legal · Joaquim Pedro de Morais Filho")
    saida.append(LINHA)
    return "\n".join(saida)


def _sintese(a: dict) -> str:
    """Parágrafo corrido de síntese, em linguagem clara."""
    frases: list[str] = []

    classe = a["classe"].lower() if a["classe"] != "não identificada" else "processo"
    sujeito = a["polo_ativo"][0] if a["polo_ativo"] else "a parte autora"
    objeto = a["polo_passivo"][0] if a["polo_passivo"] else "a parte contrária"

    frases.append(
        f"Trata-se de {classe} movida por {sujeito} em face de {objeto}"
        + (f", autuada sob o nº {a['numero_processo']}" if a["numero_processo"] != "não identificado" else "")
        + "."
    )

    if a["fundamentos_legais"]:
        frases.append(
            "A discussão apoia-se principalmente em "
            + ", ".join(a["fundamentos_legais"][:4]) + "."
        )

    if a["valores"]:
        frases.append(f"O maior valor mencionado nos autos é {max(a['valores'], key=_valor_num)}.")

    if a["decisoes"]:
        principal = next(
            (d for d in a["decisoes"]
             if d.lower().startswith(("julgo", "condeno", "absolvo", "dou provimento", "nego provimento"))),
            a["decisoes"][0],
        )
        frases.append(f"Destaca-se a decisão: \"{principal}\".")

    frases.append(f"O processo encontra-se na fase de {a['fase']}.")

    if a["prazos"]:
        frases.append(f"Atenção ao prazo detectado: {a['prazos'][0]}.")

    texto = " ".join(frases)
    # Quebra suave em ~76 colunas para leitura confortável no terminal.
    palavras, linhas, atual = texto.split(), [], "  "
    for p in palavras:
        if len(atual) + len(p) + 1 > 76:
            linhas.append(atual)
            atual = "  " + p
        else:
            atual += (" " if atual.strip() else "") + p
    linhas.append(atual)
    return "\n".join(linhas)


def _valor_num(valor: str) -> float:
    try:
        return float(valor.replace("R$", "").strip().replace(".", "").replace(",", "."))
    except ValueError:
        return 0.0
