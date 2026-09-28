from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Iterable

from models.orcamento import Orcamento, StatusOrcamento
from models.transacao import Transacao
from utils.excecoes import (
    SaldoInsuficienteError,
    TransacaoDuplicadaError,
    TransacaoNaoEncontradaError,
    ValorInvalidoError,
)
from utils.formatacao import to_decimal


class ContaBancaria:
    """Conta de um titular com saldo, histórico e orçamento.

    """Composição: a conta possui seu Orcamento e sua lista de
      Transacao, sem a conta, esses objetos não têm razão de existir.
    """ Encapsulamento: saldo e histórico são privados. O saldo só muda
      via ``registrar_transacao``/``remover_transacao``, nunca por atribuição
      direta, o que garante a invariante *saldo = inicial + Σ transações*.
    """

    def __init__(
        self,
        titular: str,
        saldo_inicial: Decimal | float | int | str = 0,
        orcamento: Orcamento | None = None,
    ) -> None:
        if not isinstance(titular, str) or not titular.strip():
            raise ValorInvalidoError("O titular não pode ser vazio.")
        inicial = to_decimal(saldo_inicial)
        if inicial < 0:
            raise ValorInvalidoError("O saldo inicial não pode ser negativo.")
        self.__titular: str = titular.strip()
        self.__saldo_inicial: Decimal = inicial
        self.__saldo: Decimal = inicial
        self.__transacoes: list[Transacao] = []
        self.__orcamento: Orcamento = orcamento if orcamento is not None else Orcamento()

    # ------------------------------------------------------------------
    # Propriedades (somente leitura)
    # ------------------------------------------------------------------
    @property
    def titular(self) -> str:
        """Nome do titular da conta."""
        return self.__titular

    @property
    def saldo(self) -> Decimal:
        """Saldo atual (somente leitura)."""
        return self.__saldo

    @property
    def saldo_inicial(self) -> Decimal:
        """Saldo com que a conta foi aberta."""
        return self.__saldo_inicial

    @property
    def orcamento(self) -> Orcamento:
        """Orçamento associado à conta."""
        return self.__orcamento

    @property
    def transacoes(self) -> tuple[Transacao, ...]:
        """Histórico imutável (tupla) em ordem de registro."""
        return tuple(self.__transacoes)

    # ------------------------------------------------------------------
    # Operações
    # ------------------------------------------------------------------
    def registrar_transacao(self, transacao: Transacao, *, ignorar_orcamento: bool = False) -> None:
        """Registra uma transação, validando saldo e orçamento.

        O código usa apenas a interface de ``Transacao`` (``aplicar`` e
        ``sujeita_a_orcamento``) — não sabe se é despesa ou receita
        (polimorfismo).

        Raises:
            TransacaoDuplicadaError: se o ``id`` já existir.
            SaldoInsuficienteError: se o saldo ficasse negativo.
            LimiteOrcamentoExcedidoError: se estourar o limite da categoria.
        """
        if not isinstance(transacao, Transacao):
            raise ValorInvalidoError("Só é possível registrar objetos do tipo Transacao.")
        if any(t.id == transacao.id for t in self.__transacoes):
            raise TransacaoDuplicadaError(f"Já existe transação com id {transacao.id}.")

        novo_saldo = transacao.aplicar(self.__saldo)
        if novo_saldo < 0:
            raise SaldoInsuficienteError(self.__saldo, transacao.valor)

        if transacao.sujeita_a_orcamento and not ignorar_orcamento:
            gasto = self.gastos_por_categoria(transacao.data.year, transacao.data.month).get(
                transacao.categoria, Decimal("0.00")
            )
            self.__orcamento.validar(transacao, gasto)

        self.__transacoes.append(transacao)
        self.__saldo = novo_saldo

    def remover_transacao(self, id_transacao: str) -> Transacao:
        """Remove uma transação e recalcula o saldo.

        Raises:
            TransacaoNaoEncontradaError: se o id não existir.
            SaldoInsuficienteError: se a remoção deixasse o saldo negativo
                (ex.: remover uma receita já gasta). Nesse caso nada muda.
        """
        alvo = next((t for t in self.__transacoes if t.id == id_transacao), None)
        if alvo is None:
            raise TransacaoNaoEncontradaError(f"Transação '{id_transacao}' não encontrada.")
        restantes = [t for t in self.__transacoes if t is not alvo]
        novo_saldo = self._calcular_saldo(restantes)
        if novo_saldo < 0:
            raise SaldoInsuficienteError(self.__saldo, alvo.valor)
        self.__transacoes = restantes
        self.__saldo = novo_saldo
        return alvo

    def _calcular_saldo(self, transacoes: Iterable[Transacao]) -> Decimal:
        """Reaplica ``transacoes`` sobre o saldo inicial (polimorfismo)."""
        saldo = self.__saldo_inicial
        for transacao in transacoes:
            saldo = transacao.aplicar(saldo)
        return saldo

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def listar_transacoes(
        self,
        tipo: str | None = None,
        categoria: str | None = None,
        ano: int | None = None,
        mes: int | None = None,
    ) -> list[Transacao]:
        """Filtra o histórico e devolve em ordem cronológica."""
        categoria_norm = categoria.strip().title() if categoria else None
        filtradas = [
            t
            for t in self.__transacoes
            if (tipo is None or t.tipo == tipo)
            and (categoria_norm is None or t.categoria == categoria_norm)
            and (ano is None or t.data.year == ano)
            and (mes is None or t.data.month == mes)
        ]
        return sorted(filtradas, key=lambda t: t.data)

    def total_por_tipo(self, tipo: str, ano: int | None = None, mes: int | None = None) -> Decimal:
        """Soma os valores de todas as transações de um tipo no período."""
        return sum(
            (t.valor for t in self.listar_transacoes(tipo=tipo, ano=ano, mes=mes)),
            Decimal("0.00"),
        )

    def gastos_por_categoria(self, ano: int, mes: int) -> dict[str, Decimal]:
        """Total de despesas por categoria no mês informado."""
        totais: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
        for despesa in self.listar_transacoes(tipo="despesa", ano=ano, mes=mes):
            totais[despesa.categoria] += despesa.valor
        return dict(totais)

    def status_orcamento(self, ano: int, mes: int) -> list[StatusOrcamento]:
        """Situação de cada limite do orçamento no mês informado."""
        return self.__orcamento.status(self.gastos_por_categoria(ano, mes))

    def resumo_mensal(self, ano: int, mes: int) -> dict[str, Decimal]:
        """Receitas, despesas e resultado (economia) do mês."""
        receitas = self.total_por_tipo("receita", ano, mes)
        despesas = self.total_por_tipo("despesa", ano, mes)
        return {"receitas": receitas, "despesas": despesas, "resultado": receitas - despesas}

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serializa a conta inteira (incluindo orçamento e histórico)."""
        return {
            "titular": self.titular,
            "saldo_inicial": str(self.saldo_inicial),
            "orcamento": self.__orcamento.to_dict(),
            "transacoes": [t.to_dict() for t in self.__transacoes],
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "ContaBancaria":
        """Reconstrói a conta; o saldo é recalculado a partir do histórico."""
        try:
            conta = cls(
                titular=dados["titular"],
                saldo_inicial=dados["saldo_inicial"],
                orcamento=Orcamento.from_dict(dados.get("orcamento", {})),
            )
            for item in dados.get("transacoes", []):
                conta.__transacoes.append(Transacao.from_dict(item))
        except KeyError as erro:
            raise ValorInvalidoError(f"Arquivo de dados incompleto: falta {erro}") from erro
        conta.__saldo = conta._calcular_saldo(conta.__transacoes)
        return conta

    def __len__(self) -> int:
        return len(self.__transacoes)

    def __str__(self) -> str:
        return f"Conta de {self.titular} | saldo: {self.saldo} | {len(self)} transações"
