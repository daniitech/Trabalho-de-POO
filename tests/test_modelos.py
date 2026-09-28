from __future__ import annotations

import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path

from models import ContaBancaria, Despesa, Orcamento, Receita, Transacao
from services import RepositorioJSON
from utils.excecoes import (
    LimiteOrcamentoExcedidoError,
    PersistenciaError,
    SaldoInsuficienteError,
    TransacaoDuplicadaError,
    TransacaoNaoEncontradaError,
    ValorInvalidoError,
)


class TestTransacao(unittest.TestCase):
    def test_classe_abstrata_nao_instanciavel(self) -> None:
        with self.assertRaises(TypeError):
            Transacao("x", 10, "Cat")  # type: ignore[abstract]

    def test_polimorfismo_aplicar(self) -> None:
        saldo = Decimal("100.00")
        self.assertEqual(Despesa("a", 30, "Lazer").aplicar(saldo), Decimal("70.00"))
        self.assertEqual(Receita("b", 30, "Salário").aplicar(saldo), Decimal("130.00"))

    def test_polimorfismo_resumo(self) -> None:
        for t in (Despesa("Pizza", 50, "Alimentação"), Receita("Bônus", 50, "Salário")):
            self.assertIn(t.descricao, t.get_resumo())
        self.assertIn("DESPESA", Despesa("x", 1, "c").get_resumo())
        self.assertIn("RECEITA", Receita("x", 1, "c").get_resumo())

    def test_encapsulamento(self) -> None:
        t = Despesa("Cinema", 40, "lazer")
        self.assertEqual(t.categoria, "Lazer")  # normalizada
        with self.assertRaises(AttributeError):
            t.id = "novo"  # type: ignore[misc]
        with self.assertRaises(ValorInvalidoError):
            t.valor = -5

    def test_validacoes(self) -> None:
        with self.assertRaises(ValorInvalidoError):
            Despesa("", 10, "Cat")
        with self.assertRaises(ValorInvalidoError):
            Despesa("ok", "abc", "Cat")
        with self.assertRaises(ValorInvalidoError):
            Despesa("ok", 0, "Cat")
        with self.assertRaises(ValorInvalidoError):
            Despesa("ok", 5, "Cat", data="31/02/2026")

    def test_valor_formato_brasileiro(self) -> None:
        self.assertEqual(Receita("x", "1.234,56", "Cat").valor, Decimal("1234.56"))

    def test_from_dict_reconstroi_subclasse(self) -> None:
        original = Receita("Freela", "200", "Extra", "15/03/2026", fonte="cliente")
        copia = Transacao.from_dict(original.to_dict())
        self.assertIsInstance(copia, Receita)
        self.assertEqual(copia.id, original.id)
        self.assertEqual(copia.data, date(2026, 3, 15))
        with self.assertRaises(ValorInvalidoError):
            Transacao.from_dict({"tipo": "inexistente"})


class TestOrcamento(unittest.TestCase):
    def test_validar_dentro_e_fora_do_limite(self) -> None:
        orc = Orcamento({"alimentação": 300})
        orc.validar(Despesa("a", 100, "Alimentação"), Decimal("150"))  # ok
        with self.assertRaises(LimiteOrcamentoExcedidoError):
            orc.validar(Despesa("b", 100, "Alimentação"), Decimal("250"))

    def test_categoria_sem_limite_e_livre(self) -> None:
        Orcamento().validar(Despesa("a", 9999, "Viagem"), Decimal("0"))

    def test_status(self) -> None:
        orc = Orcamento({"Lazer": 100, "Casa": 100, "Comida": 100})
        status = {s.categoria: s.situacao for s in orc.status(
            {"Lazer": Decimal("50"), "Casa": Decimal("85"), "Comida": Decimal("120")})}
        self.assertEqual(status, {"Lazer": "OK", "Casa": "ALERTA", "Comida": "ESTOURADO"})

    def test_limites_somente_leitura(self) -> None:
        with self.assertRaises(TypeError):
            Orcamento({"a": 1}).limites["b"] = Decimal(1)  # type: ignore[index]


class TestContaBancaria(unittest.TestCase):
    def setUp(self) -> None:
        self.conta = ContaBancaria("Ana", 1000)

    def test_saldo_somente_leitura(self) -> None:
        with self.assertRaises(AttributeError):
            self.conta.saldo = Decimal(1)  # type: ignore[misc]

    def test_registrar_atualiza_saldo(self) -> None:
        self.conta.registrar_transacao(Receita("Salário", 500, "Salário"))
        self.conta.registrar_transacao(Despesa("Mercado", 200, "Alimentação"))
        self.assertEqual(self.conta.saldo, Decimal("1300.00"))
        self.assertEqual(len(self.conta), 2)

    def test_saldo_insuficiente(self) -> None:
        with self.assertRaises(SaldoInsuficienteError):
            self.conta.registrar_transacao(Despesa("TV", 5000, "Casa"))
        self.assertEqual(self.conta.saldo, Decimal("1000.00"))

    def test_orcamento_bloqueia_despesa(self) -> None:
        self.conta.orcamento.definir_limite("Lazer", 100)
        d1 = Despesa("Show", 80, "Lazer", "10/05/2026")
        self.conta.registrar_transacao(d1)
        with self.assertRaises(LimiteOrcamentoExcedidoError):
            self.conta.registrar_transacao(Despesa("Bar", 30, "Lazer", "20/05/2026"))
        # Outro mês tem orçamento novo
        self.conta.registrar_transacao(Despesa("Bar", 30, "Lazer", "02/06/2026"))
        # Forçar ignorando orçamento
        self.conta.registrar_transacao(Despesa("Extra", 90, "Lazer", "22/05/2026"), ignorar_orcamento=True)

    def test_receita_nao_consome_orcamento(self) -> None:
        self.conta.orcamento.definir_limite("Salário", 10)
        self.conta.registrar_transacao(Receita("Pagto", 5000, "Salário"))

    def test_duplicada(self) -> None:
        t = Receita("x", 10, "Cat")
        self.conta.registrar_transacao(t)
        with self.assertRaises(TransacaoDuplicadaError):
            self.conta.registrar_transacao(t)

    def test_remover(self) -> None:
        d = Despesa("x", 100, "Cat")
        self.conta.registrar_transacao(d)
        self.conta.remover_transacao(d.id)
        self.assertEqual(self.conta.saldo, Decimal("1000.00"))
        with self.assertRaises(TransacaoNaoEncontradaError):
            self.conta.remover_transacao("nao-existe")

    def test_remover_receita_gasta_e_bloqueado(self) -> None:
        r = Receita("x", 500, "Cat")
        self.conta.registrar_transacao(r)
        self.conta.registrar_transacao(Despesa("y", 1400, "Cat"))
        with self.assertRaises(SaldoInsuficienteError):
            self.conta.remover_transacao(r.id)
        self.assertEqual(len(self.conta), 2)

    def test_historico_imutavel(self) -> None:
        self.assertIsInstance(self.conta.transacoes, tuple)

    def test_relatorios(self) -> None:
        self.conta.registrar_transacao(Receita("Sal", 3000, "Salário", "05/04/2026"))
        self.conta.registrar_transacao(Despesa("A", 400, "Alimentação", "06/04/2026"))
        self.conta.registrar_transacao(Despesa("B", 100, "Alimentação", "07/04/2026"))
        self.assertEqual(self.conta.gastos_por_categoria(2026, 4), {"Alimentação": Decimal("500.00")})
        self.assertEqual(self.conta.resumo_mensal(2026, 4)["resultado"], Decimal("2500.00"))
        self.assertEqual(len(self.conta.listar_transacoes(tipo="despesa")), 2)

    def test_titular_e_saldo_inicial_invalidos(self) -> None:
        with self.assertRaises(ValorInvalidoError):
            ContaBancaria("  ")
        with self.assertRaises(ValorInvalidoError):
            ContaBancaria("Ana", -1)


class TestPersistencia(unittest.TestCase):
    def test_ida_e_volta(self) -> None:
        conta = ContaBancaria("Bruno", "2500,50")
        conta.orcamento.definir_limite("Lazer", 300)
        conta.registrar_transacao(Receita("Salário", 4000, "Salário", "01/05/2026", fonte="Empresa"))
        conta.registrar_transacao(Despesa("Cinema", 60, "Lazer", "03/05/2026", forma_pagamento="pix"))
        with tempfile.TemporaryDirectory() as pasta:
            repo = RepositorioJSON(Path(pasta) / "sub" / "dados.json")
            self.assertIsNone(repo.carregar())  # arquivo ainda não existe
            repo.salvar(conta)
            carregada = repo.carregar()
        assert carregada is not None
        self.assertEqual(carregada.titular, "Bruno")
        self.assertEqual(carregada.saldo, conta.saldo)
        self.assertEqual(carregada.orcamento.obter_limite("Lazer"), Decimal("300.00"))
        self.assertEqual([type(t) for t in carregada.transacoes], [Receita, Despesa])

    def test_arquivo_corrompido(self) -> None:
        with tempfile.TemporaryDirectory() as pasta:
            caminho = Path(pasta) / "dados.json"
            caminho.write_text("{ isto não é json", encoding="utf-8")
            with self.assertRaises(PersistenciaError):
                RepositorioJSON(caminho).carregar()
            caminho.write_text('{"versao":1,"conta":{"titular":"X"}}', encoding="utf-8")
            with self.assertRaises(PersistenciaError):
                RepositorioJSON(caminho).carregar()


if __name__ == "__main__":
    unittest.main(verbosity=2)
