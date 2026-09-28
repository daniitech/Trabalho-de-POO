"""Sistema de Gestão Financeira Pessoal - menu interativo via terminal.

Execute:  python main.py            (menu interativo)
          python main.py --demo     (demonstração automática dos conceitos de POO)

Os dados são salvos automaticamente em ``data/dados.json`` a cada alteração.
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from models import ContaBancaria, Despesa, Receita
from services.demonstracao import executar_demonstracao, popular_exemplo
from services.persistencia import RepositorioJSON
from utils.excecoes import FinancasError, LimiteOrcamentoExcedidoError, PersistenciaError
from utils.formatacao import formatar_moeda, parse_data, to_decimal

CAMINHO_DADOS: Path = Path(__file__).resolve().parent / "data" / "dados.json"

MENU: str = """
==================== GESTÃO FINANCEIRA ====================
 1) Registrar receita          6) Status do orçamento (mês)
 2) Registrar despesa          7) Resumo mensal
 3) Extrato / filtros          8) Dados da conta
 4) Remover transação          9) Demonstração automática (POO)
 5) Orçamento (limites)       10) Carregar dados de exemplo
                               0) Sair
===========================================================
"""


class AplicacaoFinancas:
    """Controlador do menu: conecta a interface de terminal ao modelo.

    Toda regra de negócio fica em ``models``; aqui há apenas leitura de
    dados, chamadas ao modelo e exibição de resultados (separação de
    responsabilidades).
    """

    def __init__(self, repositorio: RepositorioJSON) -> None:
        self.__repositorio: RepositorioJSON = repositorio
        self.__conta: ContaBancaria = self._inicializar_conta()

    # ------------------------------------------------------------------
    # Entrada de dados (cada leitor repete até receber um valor válido)
    # ------------------------------------------------------------------
    @staticmethod
    def _ler_texto(prompt: str, obrigatorio: bool = True, padrao: str = "") -> str:
        while True:
            texto = input(prompt).strip() or padrao
            if texto or not obrigatorio:
                return texto
            print("  ! Campo obrigatório.")

    @staticmethod
    def _ler_valor(prompt: str, permitir_zero: bool = False) -> Decimal:
        while True:
            try:
                valor = to_decimal(input(prompt))
                if valor < 0 or (valor == 0 and not permitir_zero):
                    print("  ! Informe um valor positivo.")
                    continue
                return valor
            except FinancasError as erro:
                print(f"  ! {erro}")

    @staticmethod
    def _ler_data(prompt: str) -> date:
        while True:
            texto = input(prompt).strip()
            if not texto:
                return date.today()
            try:
                return parse_data(texto)
            except FinancasError as erro:
                print(f"  ! {erro}")

    @staticmethod
    def _ler_mes_ano() -> tuple[int, int]:
        """Lê 'mm/aaaa'; vazio = mês atual."""
        hoje = date.today()
        while True:
            texto = input(f"Mês/ano [mm/aaaa, Enter = {hoje.month:02d}/{hoje.year}]: ").strip()
            if not texto:
                return hoje.year, hoje.month
            try:
                mes, ano = (int(p) for p in texto.split("/"))
                if 1 <= mes <= 12 and ano >= 1900:
                    return ano, mes
            except ValueError:
                pass
            print("  ! Formato inválido. Exemplo: 09/2026")

    @staticmethod
    def _confirmar(pergunta: str) -> bool:
        return input(f"{pergunta} [s/N]: ").strip().lower() in {"s", "sim", "y"}

    # ------------------------------------------------------------------
    # Inicialização e persistência
    # ------------------------------------------------------------------
    def _inicializar_conta(self) -> ContaBancaria:
        """Carrega a conta salva ou cria uma nova."""
        try:
            conta = self.__repositorio.carregar()
            if conta is not None:
                print(f"Dados carregados: {conta}")
                return conta
        except PersistenciaError as erro:
            print(f"! {erro}")
            backup = self.__repositorio.caminho.with_suffix(".corrompido.bak")
            self.__repositorio.caminho.replace(backup)
            print(f"  O arquivo problemático foi preservado em: {backup.name}")

        print("Bem-vindo! Vamos criar sua conta.")
        while True:
            try:
                titular = self._ler_texto("Nome do titular: ")
                saldo = self._ler_valor("Saldo inicial (R$): ", permitir_zero=True)
                conta = ContaBancaria(titular, saldo)
                break
            except FinancasError as erro:
                print(f"  ! {erro}")
        self.__conta = conta
        self._salvar()
        return conta

    def _salvar(self) -> None:
        """Persiste a conta; falhas são exibidas sem derrubar o programa."""
        try:
            self.__repositorio.salvar(self.__conta)
        except PersistenciaError as erro:
            print(f"  ! ATENÇÃO: {erro}")

    # ------------------------------------------------------------------
    # Opções do menu
    # ------------------------------------------------------------------
    def _registrar_receita(self) -> None:
        print("\n--- Nova receita ---")
        receita = Receita(
            descricao=self._ler_texto("Descrição: "),
            valor=self._ler_valor("Valor (R$): "),
            categoria=self._ler_texto("Categoria (ex.: Salário): "),
            data=self._ler_data("Data [dd/mm/aaaa, Enter = hoje]: "),
            fonte=self._ler_texto("Fonte (opcional): ", obrigatorio=False),
        )
        self.__conta.registrar_transacao(receita)
        print(f"  ✔ Registrada. Novo saldo: {formatar_moeda(self.__conta.saldo)}")

    def _registrar_despesa(self) -> None:
        print("\n--- Nova despesa ---")
        despesa = Despesa(
            descricao=self._ler_texto("Descrição: "),
            valor=self._ler_valor("Valor (R$): "),
            categoria=self._ler_texto("Categoria (ex.: Alimentação): "),
            data=self._ler_data("Data [dd/mm/aaaa, Enter = hoje]: "),
            forma_pagamento=self._ler_texto("Forma de pagamento (opcional): ", obrigatorio=False),
        )
        try:
            self.__conta.registrar_transacao(despesa)
        except LimiteOrcamentoExcedidoError as erro:
            # Estourar o limite é um aviso que o usuário pode aceitar conscientemente.
            print(f"  ! {erro}")
            if not self._confirmar("  Registrar mesmo assim?"):
                print("  Despesa cancelada.")
                return
            self.__conta.registrar_transacao(despesa, ignorar_orcamento=True)
        print(f"  ✔ Registrada. Novo saldo: {formatar_moeda(self.__conta.saldo)}")
        self._alertar_categoria(despesa)

    def _alertar_categoria(self, despesa: Despesa) -> None:
        """Avisa se a categoria da despesa entrou em alerta ou estourou."""
        for status in self.__conta.status_orcamento(despesa.data.year, despesa.data.month):
            if status.categoria == despesa.categoria and status.situacao != "OK":
                print(f"  ⚠ {status.categoria}: {status.percentual}% do limite ({status.situacao}).")

    def _extrato(self) -> None:
        print("\n--- Extrato (Enter = sem filtro) ---")
        tipo = self._ler_texto("Tipo [receita/despesa]: ", obrigatorio=False).lower() or None
        if tipo not in (None, "receita", "despesa"):
            print("  ! Tipo inválido.")
            return
        categoria = self._ler_texto("Categoria: ", obrigatorio=False) or None
        periodo = self._ler_texto("Filtrar por mês? [mm/aaaa]: ", obrigatorio=False)
        ano = mes = None
        if periodo:
            try:
                mes, ano = (int(p) for p in periodo.split("/"))
            except ValueError:
                print("  ! Período inválido.")
                return
        itens = self.__conta.listar_transacoes(tipo, categoria, ano, mes)
        if not itens:
            print("  Nenhuma transação encontrada.")
            return
        print()
        for item in itens:
            print(item.get_resumo())  # polimorfismo: cada classe formata a sua linha
        print(f"\n{len(itens)} transação(ões). Saldo atual: {formatar_moeda(self.__conta.saldo)}")

    def _remover(self) -> None:
        print("\n--- Remover transação ---")
        if not self.__conta.transacoes:
            print("  Nenhuma transação registrada.")
            return
        for item in self.__conta.listar_transacoes():
            print(item.get_resumo())
        id_alvo = self._ler_texto("\nID a remover (Enter cancela): ", obrigatorio=False)
        if id_alvo and self._confirmar(f"  Confirmar remoção de {id_alvo}?"):
            removida = self.__conta.remover_transacao(id_alvo)
            print(f"  ✔ Removida: {removida.descricao}. Saldo: {formatar_moeda(self.__conta.saldo)}")

    def _menu_orcamento(self) -> None:
        print("\n--- Orçamento mensal por categoria ---")
        for cat, lim in self.__conta.orcamento.limites.items():
            print(f"  {cat}: {formatar_moeda(lim)}")
        if not len(self.__conta.orcamento):
            print("  (nenhum limite definido)")
        opcao = self._ler_texto("\n[D]efinir limite, [R]emover limite, Enter volta: ", obrigatorio=False).lower()
        if opcao == "d":
            categoria = self._ler_texto("Categoria: ")
            self.__conta.orcamento.definir_limite(categoria, self._ler_valor("Limite mensal (R$): "))
            print("  ✔ Limite definido.")
        elif opcao == "r":
            removido = self.__conta.orcamento.remover_limite(self._ler_texto("Categoria: "))
            print("  ✔ Limite removido." if removido else "  Categoria sem limite.")

    def _status_orcamento(self) -> None:
        ano, mes = self._ler_mes_ano()
        status = self.__conta.status_orcamento(ano, mes)
        if not status:
            print("  Nenhum limite definido. Use a opção 5.")
            return
        print(f"\n--- Orçamento {mes:02d}/{ano} ---")
        for s in status:
            barra = "█" * min(int(s.percentual / 10), 10)
            print(
                f"{s.categoria:<14} {formatar_moeda(s.gasto):>12} / {formatar_moeda(s.limite):>12} "
                f"{s.percentual:>6}% {barra:<10} {s.situacao}"
            )

    def _resumo_mensal(self) -> None:
        ano, mes = self._ler_mes_ano()
        resumo = self.__conta.resumo_mensal(ano, mes)
        print(f"\n--- Resumo {mes:02d}/{ano} ---")
        print(f"Receitas : {formatar_moeda(resumo['receitas'])}")
        print(f"Despesas : {formatar_moeda(resumo['despesas'])}")
        print(f"Resultado: {formatar_moeda(resumo['resultado'])}")
        gastos = self.__conta.gastos_por_categoria(ano, mes)
        if gastos:
            print("\nGastos por categoria:")
            for cat, total in sorted(gastos.items(), key=lambda par: par[1], reverse=True):
                print(f"  {cat:<16} {formatar_moeda(total):>14}")

    def _dados_conta(self) -> None:
        conta = self.__conta
        print(f"\nTitular      : {conta.titular}")
        print(f"Saldo inicial: {formatar_moeda(conta.saldo_inicial)}")
        print(f"Saldo atual  : {formatar_moeda(conta.saldo)}")
        print(f"Transações   : {len(conta)}")
        print(f"Arquivo      : {self.__repositorio.caminho}")

    def _carregar_exemplo(self) -> None:
        if not self._confirmar("Adicionar dados de exemplo à conta atual?"):
            return
        popular_exemplo(self.__conta)
        print(f"  ✔ Dados de exemplo adicionados. Saldo: {formatar_moeda(self.__conta.saldo)}")

    # ------------------------------------------------------------------
    # Laço principal
    # ------------------------------------------------------------------
    def executar(self) -> None:
        """Executa o menu até o usuário sair. Salva após cada alteração."""
        acoes = {
            "1": self._registrar_receita, "2": self._registrar_despesa,
            "3": self._extrato, "4": self._remover, "5": self._menu_orcamento,
            "6": self._status_orcamento, "7": self._resumo_mensal,
            "8": self._dados_conta, "9": executar_demonstracao,
            "10": self._carregar_exemplo,
        }
        while True:
            print(MENU)
            try:
                opcao = input("Escolha uma opção: ").strip()
                if opcao == "0":
                    break
                acao = acoes.get(opcao)
                if acao is None:
                    print("  ! Opção inválida.")
                    continue
                acao()
                self._salvar()
            except FinancasError as erro:  # erros de negócio: mensagem amigável
                print(f"  ✖ {erro}")
            except (EOFError, KeyboardInterrupt):
                print("\nEncerrando...")
                break
        self._salvar()
        print("Dados salvos. Até logo!")


def main() -> None:
    """Ponto de entrada."""
    if "--demo" in sys.argv:
        executar_demonstracao()
        return
    AplicacaoFinancas(RepositorioJSON(CAMINHO_DADOS)).executar()


if __name__ == "__main__":
    main()
