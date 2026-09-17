"""
Analisador de processos jurídicos da InpioJus.

Extrai, de peças e autos em texto, a estrutura essencial do processo:
numeração CNJ, partes, juízo, classe da ação, fundamentos legais
citados, valores, datas, pedidos, decisões e prazos. O resultado
alimenta o gerador de resumos e a memória da IA.

Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import re

# ----------------------------------------------------------------------
# Expressões regulares do domínio jurídico brasileiro
# ----------------------------------------------------------------------

RE_NUMERO_CNJ = re.compile(r"\b(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})\b")

RE_PARTE = re.compile(
    r"^\s*(AUTOR(?:A)?|R[ÉE]U?|R[ÉE]|REQUERENTE|REQUERIDO(?:A)?|RECLAMANTE|"
    r"RECLAMAD[OA]|EXEQUENTE|EXECUTAD[OA]|APELANTE|APELAD[OA]|AGRAVANTE|"
    r"AGRAVAD[OA]|EMBARGANTE|EMBARGAD[OA]|IMPETRANTE|IMPETRAD[OA]|"
    r"DENUNCIAD[OA]|INDICIAD[OA]|VÍTIMA|VITIMA)\s*(?:\(S\))?\s*[:\-–]\s*(.+?)\s*$",
    re.IGNORECASE | re.MULTILINE,
)

RE_JUIZO = re.compile(
    r"((?:\d{1,3}[ªº]?\s+)?(?:VARA|JUIZADO|TURMA|C[ÂA]MARA|SE[ÇC][ÃA]O)\b[^\n,.;]{0,70})",
    re.IGNORECASE,
)

RE_TRIBUNAL = re.compile(
    r"\b(SUPREMO TRIBUNAL FEDERAL|SUPERIOR TRIBUNAL DE JUSTI[ÇC]A|"
    r"TRIBUNAL SUPERIOR DO TRABALHO|TRIBUNAL DE JUSTI[ÇC]A[^\n,.;]{0,40}|"
    r"TRIBUNAL REGIONAL(?: FEDERAL| DO TRABALHO| ELEITORAL)[^\n,.;]{0,30}|"
    r"\bSTF\b|\bSTJ\b|\bTST\b|TJ[A-Z]{2}\b|TRF-?\d\b|TRT-?\d{1,2}\b)",
    re.IGNORECASE,
)

RE_LEI = re.compile(
    r"\b(Lei(?:\s+Complementar)?\s+n?[ºo°.]?\s*[\d.]+(?:/\d{2,4})?|"
    r"Decreto(?:-Lei)?\s+n?[ºo°.]?\s*[\d.]+(?:/\d{2,4})?|"
    r"S[úu]mula(?:\s+Vinculante)?\s+n?[ºo°.]?\s*\d+|"
    r"CF(?:/88)?\b|Constitui[çc][ãa]o Federal|C[óo]digo Civil|"
    r"C[óo]digo Penal|C[óo]digo de Processo Civil|C[óo]digo de Processo Penal|"
    r"C[óo]digo de Defesa do Consumidor|CLT\b|CPC(?:/2015)?\b|CPP\b|CDC\b|CTN\b|ECA\b)",
    re.IGNORECASE,
)

RE_ARTIGO = re.compile(
    r"\b(art(?:igo)?s?\.?\s*\d+[ºo°]?(?:\s*,?\s*(?:caput|§+\s*\d+[ºo°]?|"
    r"inciso\s+[IVXLC]+|[IVXLC]+|al[íi]nea\s+['\"]?[a-z]['\"]?))*"
    r"(?:\s*,?\s*(?:do|da|de)\s+[A-ZÇ][\w./ ]{1,45})?)",
    re.IGNORECASE,
)

RE_VALOR = re.compile(r"R\$\s?[\d.]+,\d{2}")

RE_DATA = re.compile(
    r"\b(\d{1,2}/\d{1,2}/\d{2,4}|\d{1,2}\s+de\s+"
    r"(?:janeiro|fevereiro|mar[çc]o|abril|maio|junho|julho|agosto|"
    r"setembro|outubro|novembro|dezembro)\s+de\s+\d{4})\b",
    re.IGNORECASE,
)

RE_PRAZO = re.compile(
    r"\bprazo\s+(?:de\s+|comum\s+de\s+|improrrog[áa]vel\s+de\s+)?"
    r"(\d+)\s*\((?:[^)]*)\)?\s*dias?|\bprazo\s+de\s+(\d+)\s+dias?",
    re.IGNORECASE,
)

RE_CLASSE = re.compile(
    r"\b(A[ÇC][ÃA]O\s+(?:DE\s+[^\n,.;]{3,60}|DECLARAT[ÓO]RIA[^\n,.;]{0,50}|PENAL|[^\n,.;]{3,60})|"
    r"RECLAMA[ÇC][ÃA]O TRABALHISTA|MANDADO DE SEGURAN[ÇC]A|HABEAS CORPUS|"
    r"EXECU[ÇC][ÃA]O(?:\s+FISCAL| DE T[ÍI]TULO[^\n,.;]{0,40})?|"
    r"CUMPRIMENTO DE SENTEN[ÇC]A|A[ÇC][ÃA]O PENAL|INQU[ÉE]RITO POLICIAL|"
    r"AGRAVO DE INSTRUMENTO|APELA[ÇC][ÃA]O(?:\s+C[ÍI]VEL| CRIMINAL)?|"
    r"RECURSO(?:\s+ESPECIAL| EXTRAORDIN[ÁA]RIO| ORDIN[ÁA]RIO| INOMINADO)?|"
    r"EMBARGOS(?:\s+DE DECLARA[ÇC][ÃA]O| [ÀA] EXECU[ÇC][ÃA]O)?|"
    r"USUCAPI[ÃA]O|DIV[ÓO]RCIO[^\n,.;]{0,30}|INVENT[ÁA]RIO|"
    r"ALIMENTOS|REINTEGRA[ÇC][ÃA]O DE POSSE|DESPEJO[^\n,.;]{0,30})",
    re.IGNORECASE,
)

# Trecho de sentença: avança até o ponto final, mas atravessa as
# abreviações comuns "art.", "arts.", "nº." e "fls." sem parar.
_TRECHO = r"(?:[^.;]|\.(?=\d)|(?<=\bart)\.|(?<=\barts)\.|(?<=\bfls)\.|(?<=\bn)\.)"

RE_DECISAO = re.compile(
    r"\b(julgo\s+(?:parcialmente\s+)?(?:im)?procedentes?" + _TRECHO + r"{0,180}|"
    r"julgo\s+extint[oa]" + _TRECHO + r"{0,180}|"
    r"(?:defiro|indefiro)" + _TRECHO + r"{0,180}|"
    r"(?:concedo|denego)" + _TRECHO + r"{0,180}|"
    r"homologo" + _TRECHO + r"{0,180}|"
    r"(?:condeno|absolvo)" + _TRECHO + r"{0,180}|"
    r"(?:dou|nego)\s+provimento" + _TRECHO + r"{0,180}|"
    r"recebo\s+a\s+den[úu]ncia" + _TRECHO + r"{0,180}|"
    r"decreto\s+a\s+(?:pris[ãa]o|revelia|fal[êe]ncia)" + _TRECHO + r"{0,180})",
    re.IGNORECASE,
)

RE_PEDIDO = re.compile(
    r"\b(?:requer(?:endo)?|pede(?:-se)?|pleiteia|postula)\b" + _TRECHO + r"{5,220}",
    re.IGNORECASE,
)

_FASES = [
    ("trânsito em julgado", ["transito em julgado", "trânsito em julgado", "transitou em julgado"]),
    ("execução / cumprimento de sentença", ["cumprimento de sentenca", "cumprimento de sentença", "fase de execucao", "fase de execução", "penhora"]),
    ("recursal", ["apelacao", "apelação", "recurso especial", "recurso extraordinario", "recurso extraordinário", "agravo de instrumento", "contrarrazoes", "contrarrazões"]),
    ("sentença", ["julgo procedente", "julgo improcedente", "julgo parcialmente", "sentenca", "sentença", "dispositivo"]),
    ("instrução", ["audiencia de instrucao", "audiência de instrução", "oitiva de testemunhas", "pericia", "perícia", "laudo pericial"]),
    ("saneamento", ["decisao de saneamento", "decisão de saneamento", "saneador"]),
    ("resposta / contestação", ["contestacao", "contestação", "reconvencao", "reconvenção", "defesa previa", "defesa prévia"]),
    ("postulatória (inicial)", ["peticao inicial", "petição inicial", "distribuido", "distribuído", "cite-se", "citacao", "citação"]),
]


def _unicos(seq: list[str], limite: int = 12) -> list[str]:
    vistos, saida = set(), []
    for item in seq:
        chave = re.sub(r"\s+", " ", item.strip().lower())
        if chave and chave not in vistos:
            vistos.add(chave)
            saida.append(re.sub(r"\s+", " ", item.strip()))
        if len(saida) >= limite:
            break
    return saida


def detectar_fase(texto: str) -> str:
    """Estima a fase processual pelo vocabulário presente nos autos."""
    plano = texto.lower()
    for fase, marcadores in _FASES:
        if any(m in plano for m in marcadores):
            return fase
    return "não identificada"


def analisar(texto: str) -> dict:
    """Analisa o texto de um processo e devolve a estrutura extraída."""
    numeros = ["{}-{}.{}.{}.{}.{}".format(*m) for m in RE_NUMERO_CNJ.findall(texto)]

    partes: dict[str, list[str]] = {}
    for papel, nome in RE_PARTE.findall(texto):
        papel_norm = papel.strip().upper()
        nome_limpo = re.sub(r"\s+", " ", nome).strip(" .;,-–")
        if nome_limpo:
            partes.setdefault(papel_norm, [])
            if nome_limpo not in partes[papel_norm]:
                partes[papel_norm].append(nome_limpo)

    valores = _unicos(RE_VALOR.findall(texto), 10)
    leis = _unicos([m if isinstance(m, str) else m[0] for m in RE_LEI.findall(texto)], 15)
    artigos = _unicos([m if isinstance(m, str) else m[0] for m in RE_ARTIGO.findall(texto)], 15)
    datas = _unicos(RE_DATA.findall(texto), 12)
    juizos = _unicos(RE_JUIZO.findall(texto), 3)
    tribunais = _unicos(RE_TRIBUNAL.findall(texto), 3)
    classes = _unicos(RE_CLASSE.findall(texto), 3)
    decisoes = _unicos(RE_DECISAO.findall(texto), 8)
    pedidos = _unicos(RE_PEDIDO.findall(texto), 6)

    prazos = []
    for m in RE_PRAZO.finditer(texto):
        dias = m.group(1) or m.group(2)
        if dias:
            trecho = re.sub(r"\s+", " ", m.group(0)).strip()
            prazos.append(f"{trecho} ({dias} dias)")
    prazos = _unicos(prazos, 8)

    classe = classes[0].upper() if classes else "não identificada"
    numero = numeros[0] if numeros else "não identificado"
    fase = detectar_fase(texto)

    polo_ativo = next(
        (partes[p] for p in ("AUTOR", "AUTORA", "REQUERENTE", "RECLAMANTE",
                             "EXEQUENTE", "APELANTE", "AGRAVANTE", "EMBARGANTE",
                             "IMPETRANTE") if p in partes),
        [],
    )
    polo_passivo = next(
        (partes[p] for p in ("RÉU", "RÉ", "REU", "RE", "REQUERIDO", "REQUERIDA",
                             "RECLAMADO", "RECLAMADA", "EXECUTADO", "EXECUTADA",
                             "APELADO", "APELADA", "AGRAVADO", "AGRAVADA",
                             "EMBARGADO", "EMBARGADA", "IMPETRADO", "IMPETRADA",
                             "DENUNCIADO", "DENUNCIADA") if p in partes),
        [],
    )

    resumo_curto = (
        f"{classe if classe != 'NÃO IDENTIFICADA' else 'Processo'}"
        f" nº {numero}"
        + (f" — {polo_ativo[0]}" if polo_ativo else "")
        + (f" x {polo_passivo[0]}" if polo_passivo else "")
        + f" — fase: {fase}"
    )

    return {
        "numero_processo": numero,
        "classe": classe,
        "fase": fase,
        "partes": partes,
        "polo_ativo": polo_ativo,
        "polo_passivo": polo_passivo,
        "juizo": juizos,
        "tribunal": tribunais,
        "fundamentos_legais": leis,
        "artigos_citados": artigos,
        "valores": valores,
        "datas_relevantes": datas,
        "pedidos": pedidos,
        "decisoes": decisoes,
        "prazos": prazos,
        "resumo_curto": resumo_curto,
        "entidades": {
            "leis": leis,
            "tribunais": tribunais,
            "classes": classes,
            "juizos": juizos,
        },
        "tamanho_texto": len(texto),
    }
