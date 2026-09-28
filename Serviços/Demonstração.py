"Trabalha com uma conta em memória e um arquivo temporário, portanto não altera os dados reais do usuário.

from __future__ import annotations

import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from models import ContaBancaria, Despesa, Receita, Transacao
from services.persistencia import RepositorioJSON
from utils.excecoes import FinancasError
from utils.formatacao import formatar_moeda


def _titulo(texto: str) -> None:
    print(f"\n{'=' * 64}\n {texto}\n{'=' * 64}")


def popular_exemplo(conta: ContaBancaria) -> None:
    """Preenche ``conta`` com receitas, despesas e limites do mês atual."""
    hoje = date.today()
    conta.orcamento.definir_limite("Alimentação", 800)
    conta.orcamento.definir_limite("Lazer", 300)
    conta.orcamento.definir_limite("Transporte", 250)
    exemplos: list[Transacao] = [
        Receita("Salário", 5000, "Salário", hoje.replace(day=1), fonte="Empresa XYZ"),
        Receita("Freelance de site", 900, "Renda Extra", hoje.replace(day=5), fonte="Cliente"),
        Despesa("Supermercado", 520, "Alimentação", hoje.replace(day=3), forma_pagamento="Cartão"),
        Despesa("Restaurante", 180, "Alimentação", hoje.replace(day=8), forma_pagamento="Pix"),
        Despesa("Cinema", 70, "Lazer", hoje.replace(day=9), forma_pagamento="Cartão"),
        Despesa("Combustível", 210, "Transporte", hoje.replace(day=4), forma_pagamento="Dinheiro"),
        Despesa("Aluguel", 1500, "Moradia", hoje.replace(day=2), forma_pagamento="Boleto"),
    ]
    for transacao in exemplos:
        conta.registrar_transacao(transacao)


def executar_demonstracao() -> None:
    """Executa um roteiro que exercita cada conceito exigido pelo projeto."""
    hoje = date.today()

    _titulo("1. ABSTRAÇÃO - Transacao é uma classe abstrata (ABC)")
    try:
        Transacao("teste", 10, "X")  # type: ignore[abstract]
    except TypeError as erro:
        print(f"Não é possível instanciar: {erro}")

    conta = ContaBancaria("Aluno Demo", 1000)
    conta.orcamento.definir_limite("Lazer", 200)

    _titulo("2. HERANÇA + POLIMORFISMO - mesma chamada, comportamentos distintos")
    receita = Receita("Salário", 3000, "Salário", hoje, fonte="Empresa")
    despesa = Despesa("Cinema", 60, "Lazer", hoje, forma_pagamento="Pix")
    for transacao in (receita, despesa):  # loop trata ambas pela interface base
        novo = transacao.aplicar(conta.saldo)
        print(f"{type(transacao).__name__:8} -> aplicar(saldo={conta.saldo}) = {novo}")
        print(f"          {transacao.get_resumo()}")
        conta.registrar_transacao(transacao)

    _titulo("3. ENCAPSULAMENTO - saldo protegido")
    try:
        conta.saldo = Decimal("999999")  # type: ignore[misc]
    except AttributeError as erro:
        print(f"conta.saldo = ...          -> AttributeError: {erro}")
    print(f"hasattr(conta, '__saldo')  -> {hasattr(conta, '__saldo')}  (atributo privado com name mangling)")
    try:
        despesa.valor = -50
    except FinancasError as erro:
        print(f"despesa.valor = -50        -> {type(erro).__name__}: {erro}")
    print(f"Saldo real (via property)  -> {formatar_moeda(conta.saldo)}")

    _titulo("4. COMPOSIÇÃO - Conta valida despesas usando o Orcamento")
    try:
        conta.registrar_transacao(Despesa("Show", 180, "Lazer", hoje))
    except FinancasError as erro:
        print(f"Bloqueado: {erro}")
    for s in conta.status_orcamento(hoje.year, hoje.month):
        print(f"{s.categoria}: {formatar_moeda(s.gasto)} de {formatar_moeda(s.limite)} ({s.percentual}%) [{s.situacao}]")

    _titulo("5. TRATAMENTO DE EXCEÇÕES - saldo insuficiente")
    try:
        conta.registrar_transacao(Despesa("Carro", 50000, "Veículo", hoje))
    except FinancasError as erro:
        print(f"Bloqueado: {erro}")

    _titulo("6. PERSISTÊNCIA JSON - salvar e recarregar")
    with tempfile.TemporaryDirectory() as pasta:
        repositorio = RepositorioJSON(Path(pasta) / "demo.json")
        repositorio.salvar(conta)
        recarregada = repositorio.carregar()
        assert recarregada is not None
        print(f"Original : {conta}")
        print(f"Recarregada: {recarregada}")
        print(f"Estados idênticos? {conta.to_dict() == recarregada.to_dict()}")
        tipos = [type(t).__name__ for t in recarregada.transacoes]
        print(f"Tipos reconstruídos pela factory: {tipos}")
    print("\nDemonstração concluída (nenhum dado real foi alterado).")
