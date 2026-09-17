"""Testes básicos da InpioJus Analitic Legal.

Execute com:  python -m unittest discover tests
"""

import os
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

from inpiojus import analisador, resumo, vetor  # noqa: E402
from inpiojus.memoria import Memoria  # noqa: E402


def _exemplo(nome: str) -> str:
    return (RAIZ / "exemplos" / nome).read_text(encoding="utf-8")


class TesteAnalisador(unittest.TestCase):
    def test_processo_civil(self):
        a = analisador.analisar(_exemplo("processo_civil_exemplo.txt"))
        self.assertEqual(a["numero_processo"], "0012345-67.2024.8.06.0001")
        self.assertIn("INDENIZAÇÃO", a["classe"])
        self.assertEqual(a["fase"], "sentença")
        self.assertIn("MARIA DAS GRAÇAS OLIVEIRA SANTOS", a["polo_ativo"])
        self.assertTrue(any("BANCO HORIZONTE" in p for p in a["polo_passivo"]))
        self.assertIn("R$ 31.900,00", a["valores"])
        self.assertTrue(any("julgo parcialmente procedentes" in d.lower()
                            for d in a["decisoes"]))

    def test_processo_trabalhista(self):
        a = analisador.analisar(_exemplo("processo_trabalhista_exemplo.txt"))
        self.assertEqual(a["numero_processo"], "0001234-55.2024.5.07.0005")
        self.assertEqual(a["classe"], "RECLAMAÇÃO TRABALHISTA")
        self.assertTrue(any("CLT" in lei for lei in a["fundamentos_legais"]))

    def test_processo_penal(self):
        a = analisador.analisar(_exemplo("processo_penal_exemplo.txt"))
        self.assertEqual(a["classe"], "AÇÃO PENAL")
        self.assertEqual(a["fase"], "instrução")
        self.assertTrue(any("recebo a denúncia" in d.lower() for d in a["decisoes"]))

    def test_resumo_gerado(self):
        a = analisador.analisar(_exemplo("processo_civil_exemplo.txt"))
        texto = resumo.gerar(a)
        self.assertIn("SÍNTESE", texto)
        self.assertIn("Trata-se de", texto)
        self.assertIn("Joaquim Pedro de Morais Filho", texto)


class TesteVetor(unittest.TestCase):
    def test_similaridade_semantica(self):
        v1 = vetor.vetorizar("ação de indenização por danos morais contra banco")
        v2 = vetor.vetorizar("indenização de danos morais movida contra o banco")
        v3 = vetor.vetorizar("homologação de acordo de divórcio consensual")
        self.assertGreater(vetor.similaridade(v1, v2), vetor.similaridade(v1, v3))

    def test_vetor_normalizado(self):
        v = vetor.vetorizar("reclamação trabalhista com horas extras")
        norma = sum(x * x for x in v) ** 0.5
        self.assertAlmostEqual(norma, 1.0, places=6)


class TesteMemoria(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["INPIOJUS_MEMORIA"] = self._tmp.name

    def tearDown(self):
        os.environ.pop("INPIOJUS_MEMORIA", None)
        self._tmp.cleanup()

    def test_aprendizado_e_recuperacao(self):
        mem = Memoria()
        texto = _exemplo("processo_civil_exemplo.txt")
        mem.registrar(analisador.analisar(texto), texto)

        mem2 = Memoria()  # recarrega do disco: persistência real
        stats = mem2.estatisticas()
        self.assertEqual(stats["documentos_vistos"], 1)
        self.assertGreater(stats["vocabulario_aprendido"], 50)

        parecidos = mem2.similares(texto, k=1)
        self.assertEqual(len(parecidos), 1)
        self.assertGreater(parecidos[0]["similaridade"], 0.9)

    def test_busca_textual(self):
        mem = Memoria()
        texto = _exemplo("processo_trabalhista_exemplo.txt")
        mem.registrar(analisador.analisar(texto), texto)
        achados = mem.buscar("trabalhista")
        self.assertEqual(len(achados), 1)

    def test_apagar(self):
        mem = Memoria()
        texto = _exemplo("processo_penal_exemplo.txt")
        mem.registrar(analisador.analisar(texto), texto)
        mem.apagar()
        self.assertEqual(mem.estatisticas()["documentos_vistos"], 0)


if __name__ == "__main__":
    unittest.main()
