<div align="center">

# ⚖️ InpioJus Analitic Legal

**Inteligência artificial de análise de processos jurídicos com memória própria.**

Resumos claros em português · Memória persistente estilo LLM · 100% local, sem nuvem

Por **Joaquim Pedro de Morais Filho**

[Site oficial](https://elevbit-ai.github.io/inpiojus-analitic-legal/) ·
[🎬 Vídeo de apresentação](https://github.com/elevbit-ai/inpiojus-analitic-legal/releases/download/v1.0.0/InpioJus-Analitic-Legal-Apresentacao.mp4) ·
[Instalação](#-instalação-no-powershell) ·
[Como funciona a memória](#-a-memória-da-ia) ·
[Exemplos](#-exemplos)

</div>

---

## O que é

A **InpioJus Analitic Legal** lê autos e peças processuais em texto e produz,
em segundos, um **resumo inteligente e estruturado** do processo: partes,
classe da ação, fase processual, fundamentos legais, valores, decisões,
prazos e uma síntese em linguagem clara.

O diferencial é a **memória própria**, inspirada na arquitetura dos grandes
modelos de linguagem (LLM): cada processo analisado é convertido em um
*embedding* vetorial e consolidado em três camadas de memória. Quanto mais a
IA lê, mais ela aprende — e passa a apontar automaticamente **casos
semelhantes que já analisou**.

Tudo roda **localmente na sua máquina**, em Python puro, sem dependências
externas e sem enviar um único byte dos seus processos para a internet —
essencial para o sigilo profissional.

## 🧠 A memória da IA

| Camada | Análogo no LLM | O que guarda |
|---|---|---|
| **Curto prazo** | Janela de contexto | As últimas 12 análises, na íntegra |
| **Longo prazo** | Pesos treinados | Vocabulário jurídico aprendido (IDF incremental), entidades recorrentes, estatísticas — com decaimento suave do que deixa de aparecer |
| **Episódica** | Recuperação por atenção | Cada processo vira um episódio com embedding de 256 dimensões; a similaridade de cosseno recupera casos parecidos |

A memória fica em `~/.inpiojus/memoria` em JSON legível: você é dono dela,
pode inspecioná-la, copiá-la entre máquinas ou apagá-la com um comando.

## 🚀 Instalação no PowerShell

Uma linha (requer Python 3.9+):

```powershell
irm https://elevbit-ai.github.io/inpiojus-analitic-legal/install.ps1 | iex
```

Ou manualmente, em qualquer sistema:

```powershell
git clone https://github.com/elevbit-ai/inpiojus-analitic-legal.git
cd inpiojus-analitic-legal
python -m inpiojus --versao
```

Ou ainda via `pip`:

```powershell
pip install git+https://github.com/elevbit-ai/inpiojus-analitic-legal.git
```

## 📖 Uso

```powershell
inpiojus analisar processo.txt        # análise completa + aprendizado
inpiojus resumo processo.txt          # resumo enxuto
inpiojus similares processo.txt       # casos parecidos já analisados
inpiojus buscar "dano moral"          # pesquisa na memória
inpiojus memoria                      # o que a IA já aprendeu
inpiojus analisar processo.txt --json # saída estruturada em JSON
inpiojus limpar --confirmar           # apaga a memória
```

Também aceita texto pela entrada padrão:

```powershell
Get-Content processo.txt | inpiojus analisar -
```

## 💡 Exemplos

O repositório traz três processos fictícios completos em [`exemplos/`](exemplos/):
cível (consumidor), trabalhista e penal.

```powershell
inpiojus analisar exemplos\processo_civil_exemplo.txt
```

Saída (trecho):

```text
IDENTIFICAÇÃO
──────────────────────────────────────────────────────────────
  Processo nº ...: 0012345-67.2024.8.06.0001
  Classe ........: AÇÃO DE INDENIZAÇÃO POR DANOS MORAIS E MATERIAIS
  Fase atual ....: sentença
  Juízo .........: 3ª Vara Cível da Comarca de Fortaleza

SÍNTESE
──────────────────────────────────────────────────────────────
  Trata-se de ação de indenização por danos morais e materiais movida
  por MARIA DAS GRAÇAS OLIVEIRA SANTOS em face de BANCO HORIZONTE S.A...

MEMÓRIA DA IA — CASOS SEMELHANTES JÁ ANALISADOS
──────────────────────────────────────────────────────────────
  • [87% similar] AÇÃO DE COBRANÇA nº 0009876-11.2023.8.06.0001 ...
```

## 🔬 O que a IA extrai

- **Numeração CNJ** do processo
- **Partes** (autor/réu, reclamante/reclamada, MP/denunciado…)
- **Juízo e tribunal**
- **Classe da ação e fase processual** (postulatória → trânsito em julgado)
- **Fundamentos legais** (leis, códigos, súmulas) e **artigos citados**
- **Valores** em reais, **datas relevantes** e **prazos**
- **Pedidos** e **decisões judiciais** (procedência, condenações, deferimentos)

## 🧪 Testes

```powershell
python -m unittest discover tests
```

## 📜 Autoria e licença

Software de autoria de **Joaquim Pedro de Morais Filho**
📧 j360074@hotmail.com · 📱 +55 85 99125-3990

Licença [MIT](LICENSE) · Registro de autoria em [AUTHORS.md](AUTHORS.md)

> ⚠️ A InpioJus é uma ferramenta de apoio. Suas análises **não substituem**
> a leitura dos autos nem o parecer de um advogado.
