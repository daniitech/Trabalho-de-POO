"""Orçamento mensal com limites de gasto por categoria."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Mapping

from utils.excecoes import LimiteOrcamentoExcedidoError, ValorInvalidoError
from utils.formatacao import to_decimal

if TYPE_CHECKING:  # evita import circular em tempo de execução
    from models.transacao import Transacao


@dataclass(frozen=True)
class StatusOrcamento:
    """Situação de uma categoria em relação ao seu limite (objeto imutável)."""

    categoria: str
    limite: Decimal
    gasto: Decimal
    restante: Decimal
    percentual: Decimal
    situacao: str  # "OK", "ALERTA" (>= 80%) ou "ESTOURADO" (> 100%)


class Orcamento:
    """Guarda limites mensais por categoria e valida despesas contra eles.

    A classe é *agregada* por ``ContaBancaria`` (composição): a conta
    fornece o gasto acumulado do mês e o orçamento decide se a nova
    despesa é aceitável (responsabilidade única).
    """

    LIMIAR_ALERTA: Decimal = Decimal("0.80")

    def __init__(self, limites: Mapping[str, Any] | None = None) -> None:
        self.__limites: dict[str, Decimal] = {}
        for categoria, valor in (limites or {}).items():
            self.definir_limite(categoria, valor)

    @staticmethod
    def _normalizar(categoria: str) -> str:
        if not isinstance(categoria, str) or not categoria.strip():
            raise ValorInvalidoError("A categoria não pode ser vazia.")
        return categoria.strip().title()

    @property
    def limites(self) -> Mapping[str, Decimal]:
        """Visão somente leitura dos limites (protege o dict interno)."""
        return MappingProxyType(self.__limites)

    def definir_limite(self, categoria: str, limite: Any) -> None:
        """Define (ou atualiza) o limite mensal de uma categoria."""
        valor = to_decimal(limite)
        if valor <= 0:
            raise ValorInvalidoError("O limite deve ser maior que zero.")
        self.__limites[self._normalizar(categoria)] = valor

    def remover_limite(self, categoria: str) -> bool:
        """Remove o limite da categoria. Retorna ``True`` se existia."""
        return self.__limites.pop(self._normalizar(categoria), None) is not None

    def obter_limite(self, categoria: str) -> Decimal | None:
        """Limite da categoria ou ``None`` se não houver."""
        return self.__limites.get(self._normalizar(categoria))

    def validar(self, despesa: "Transacao", gasto_acumulado: Decimal) -> None:
        """Garante que ``despesa`` não ultrapassa o limite mensal.

        Args:
            despesa: transação candidata.
            gasto_acumulado: total já gasto na categoria no mês da despesa.

        Raises:
            LimiteOrcamentoExcedidoError: se o gasto projetado passar do limite.
        """
        limite = self.__limites.get(despesa.categoria)
        if limite is None:
            return  # categoria sem limite é livre
        projetado = gasto_acumulado + despesa.valor
        if projetado > limite:
            raise LimiteOrcamentoExcedidoError(despesa.categoria, limite, projetado)

    def status(self, gastos_por_categoria: Mapping[str, Decimal]) -> list[StatusOrcamento]:
        """Calcula a situação de cada categoria com limite definido."""
        resultado: list[StatusOrcamento] = []
        for categoria, limite in sorted(self.__limites.items()):
            gasto = gastos_por_categoria.get(categoria, Decimal("0.00"))
            percentual = (gasto / limite * 100).quantize(Decimal("0.1"))
            if gasto > limite:
                situacao = "ESTOURADO"
            elif gasto >= limite * self.LIMIAR_ALERTA:
                situacao = "ALERTA"
            else:
                situacao = "OK"
            resultado.append(
                StatusOrcamento(categoria, limite, gasto, limite - gasto, percentual, situacao)
            )
        return resultado

    def to_dict(self) -> dict[str, str]:
        """Serializa os limites (valores como texto para não perder precisão)."""
        return {cat: str(lim) for cat, lim in self.__limites.items()}

    @classmethod
    def from_dict(cls, dados: Mapping[str, Any]) -> "Orcamento":
        """Reconstrói o orçamento a partir de um dicionário."""
        return cls(dados)

    def __len__(self) -> int:
        return len(self.__limites)

    def __repr__(self) -> str:
        return f"Orcamento(limites={self.to_dict()})"
