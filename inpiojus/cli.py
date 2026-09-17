"""
Interface de linha de comando da InpioJus Analitic Legal.

Pensada para o PowerShell e para qualquer terminal:

    inpiojus analisar processo.txt      análise completa + memória
    inpiojus resumo processo.txt        resumo enxuto
    inpiojus similares processo.txt     casos parecidos já vistos
    inpiojus buscar "dano moral"        pesquisa na memória
    inpiojus memoria                    o que a IA já aprendeu
    inpiojus limpar --confirmar         apaga a memória

Autor: Joaquim Pedro de Morais Filho <j360074@hotmail.com>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, analisador, memoria as memoria_mod, resumo


def _ler_arquivo(caminho: str) -> str:
    p = Path(caminho)
    if not p.exists():
        sys.exit(f"[InpioJus] arquivo não encontrado: {caminho}")
    dados = p.read_bytes()
    for codec in ("utf-8", "latin-1"):
        try:
            return dados.decode(codec)
        except UnicodeDecodeError:
            continue
    return dados.decode("utf-8", errors="replace")


def _texto_de_entrada(args) -> str:
    if args.arquivo == "-":
        return sys.stdin.read()
    return _ler_arquivo(args.arquivo)


def cmd_analisar(args) -> None:
    texto = _texto_de_entrada(args)
    mem = memoria_mod.Memoria()
    analise = analisador.analisar(texto)
    parecidos = mem.similares(texto, k=3, ignorar_numero=analise["numero_processo"])
    mem.registrar(analise, texto)

    if args.json:
        print(json.dumps(
            {"analise": analise, "casos_semelhantes": parecidos},
            ensure_ascii=False, indent=2,
        ))
        return

    print(resumo.gerar(analise, parecidos, mem.estatisticas(), completo=True))


def cmd_resumo(args) -> None:
    texto = _texto_de_entrada(args)
    mem = memoria_mod.Memoria()
    analise = analisador.analisar(texto)
    parecidos = mem.similares(texto, k=3, ignorar_numero=analise["numero_processo"])
    mem.registrar(analise, texto)
    print(resumo.gerar(analise, parecidos, None, completo=False))


def cmd_similares(args) -> None:
    texto = _texto_de_entrada(args)
    mem = memoria_mod.Memoria()
    parecidos = mem.similares(texto, k=args.quantidade)
    if not parecidos:
        print("[InpioJus] a memória ainda não conhece casos parecidos com este.")
        return
    print(f"[InpioJus] {len(parecidos)} caso(s) semelhante(s) na memória:\n")
    for s in parecidos:
        print(f"  {int(s['similaridade'] * 100):>3}%  {s.get('resumo_curto')}")
        print(f"        analisado em {s['quando']}\n")


def cmd_buscar(args) -> None:
    mem = memoria_mod.Memoria()
    achados = mem.buscar(args.termo, k=args.quantidade)
    if not achados:
        print(f"[InpioJus] nada na memória sobre: {args.termo}")
        return
    print(f"[InpioJus] {len(achados)} resultado(s) para \"{args.termo}\":\n")
    for a in achados:
        print(f"  • {a.get('resumo_curto')}")
        print(f"    analisado em {a['quando']}\n")


def cmd_memoria(args) -> None:
    mem = memoria_mod.Memoria()
    stats = mem.estatisticas()
    if args.json:
        print(json.dumps(stats, ensure_ascii=False, indent=2))
        return
    print("╔" + "═" * 50 + "╗")
    print("║   Memória da InpioJus — estado atual".ljust(51) + "║")
    print("╚" + "═" * 50 + "╝")
    print(f"  Local .................: {stats['diretorio']}")
    print(f"  Criada em .............: {stats['criada_em']}")
    print(f"  Processos aprendidos ..: {stats['documentos_vistos']}")
    print(f"  Episódios retidos .....: {stats['episodios_retidos']}")
    print(f"  Contexto (curto prazo) : {stats['janela_curto_prazo']} análise(s)")
    print(f"  Vocabulário jurídico ..: {stats['vocabulario_aprendido']} termos")
    if stats["termos_mais_fortes"]:
        print("\n  Termos com maior peso na memória de longo prazo:")
        print("    " + ", ".join(stats["termos_mais_fortes"]))
    if stats["entidades_recorrentes"]:
        print("\n  Entidades recorrentes:")
        for categoria, itens in stats["entidades_recorrentes"].items():
            if itens:
                topo = ", ".join(f"{nome} ({qtd}x)" for nome, qtd in itens[:3])
                print(f"    {categoria}: {topo}")


def cmd_limpar(args) -> None:
    if not args.confirmar:
        sys.exit("[InpioJus] use --confirmar para apagar a memória (irreversível).")
    mem = memoria_mod.Memoria()
    mem.apagar()
    print("[InpioJus] memória apagada. A IA recomeça do zero.")


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inpiojus",
        description=(
            "InpioJus Analitic Legal — IA de análise de processos jurídicos "
            "com memória própria. Por Joaquim Pedro de Morais Filho."
        ),
    )
    parser.add_argument("--versao", action="version",
                        version=f"InpioJus Analitic Legal v{__version__}")
    sub = parser.add_subparsers(dest="comando", required=True)

    p = sub.add_parser("analisar", help="análise completa de um processo")
    p.add_argument("arquivo", help="arquivo .txt do processo (ou - para stdin)")
    p.add_argument("--json", action="store_true", help="saída em JSON")
    p.set_defaults(func=cmd_analisar)

    p = sub.add_parser("resumo", help="resumo enxuto de um processo")
    p.add_argument("arquivo", help="arquivo .txt do processo (ou - para stdin)")
    p.set_defaults(func=cmd_resumo)

    p = sub.add_parser("similares", help="casos parecidos na memória")
    p.add_argument("arquivo", help="arquivo .txt do processo (ou - para stdin)")
    p.add_argument("-k", "--quantidade", type=int, default=5)
    p.set_defaults(func=cmd_similares)

    p = sub.add_parser("buscar", help="pesquisa textual na memória")
    p.add_argument("termo")
    p.add_argument("-k", "--quantidade", type=int, default=10)
    p.set_defaults(func=cmd_buscar)

    p = sub.add_parser("memoria", help="estado da memória da IA")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_memoria)

    p = sub.add_parser("limpar", help="apaga toda a memória")
    p.add_argument("--confirmar", action="store_true")
    p.set_defaults(func=cmd_limpar)

    return parser


def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    args = construir_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
