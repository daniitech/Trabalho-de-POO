"""Hierarquia de transações: ``Transacao`` (abstrata), ``Despesa`` e ``Receita``.

Conceitos de POO demonstrados neste módulo:
    * **Abstração**: ``Transacao`` herda de ``ABC`` e não pode ser instanciada.
    * **Encapsulamento**: atributos privados (``__nome``) expostos por
      ``property`` com validação nos setters.
    * **Herança**: ``Despesa`` e ``Receita`` reutilizam o comportamento comum.
    * **Polimorfismo**: ``aplicar()`` e ``get_resumo()`` têm implementações
      diferentes em cada subclasse, chamadas de forma uniforme.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal
from typing import Any, ClassVar

from utils.excecoes import ValorInvalidoError
from utils.formatacao import formatar_data, formatar_moeda, parse_data, to_decimal


class Transacao(ABC):
    """Classe base abstrata de uma movimentação financeira.

    Subclasses concretas devem definir o atributo de classe ``TIPO`` e
    implementar ``aplicar``, ``get_resumo``, ``_extras_dict`` e
    ``_extras_from_dict``. Ao definir ``TIPO`` a subclasse é registrada
    automaticamente (via ``__init_subclass__``), o que permite que
    ``Transacao.from_dict`` reconstrua o objeto correto a partir do JSON
    sem ``if/elif`` (princípio Aberto/Fechado).
    """

    TIPO: ClassVar[str] = ""
    _registro: ClassVar[dict[str, type["Transacao"]]] = {}

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Registra automaticamente cada subclasse concreta pelo seu ``TIPO``."""
        super().__init_subclass__(**kwargs)
        if "TIPO" in cls.__dict__ and cls.TIPO:
            Transacao._registro[cls.TIPO] = cls

    def __init__(
        self,
        descricao: str,
        valor: Decimal | float | int | str,
        categoria: str,
        data: date | str | None = None,
        id: str | None = None,  # noqa: A002 - nome escolhido por clareza do domínio
    ) -> None:
        self.__id: str = id or uuid.uuid4().hex[:8]
        # Os setters validam e normalizam os dados.
        self.descricao = descricao
        self.valor = valor
        self.categoria = categoria
        self.data = data if data is not None else date.today()

    # ------------------------------------------------------------------
    # Encapsulamento: propriedades com validação
    # ------------------------------------------------------------------
    @property
    def id(self) -> str:
        """Identificador único (somente leitura)."""
        return self.__id

    @property
    def descricao(self) -> str:
        """Descrição textual da transação."""
        return self.__descricao

    @descricao.setter
    def descricao(self, nova: str) -> None:
        if not isinstance(nova, str) or not nova.strip():
            raise ValorInvalidoError("A descrição não pode ser vazia.")
        self.__descricao = nova.strip()

    @property
    def valor(self) -> Decimal:
        """Valor monetário (sempre positivo; o sinal é dado pelo tipo)."""
        return self.__valor

    @valor.setter
    def valor(self, novo: Decimal | float | int | str) -> None:
        convertido = to_decimal(novo)
        if convertido <= 0:
            raise ValorInvalidoError("O valor da transação deve ser positivo.")
        self.__valor = convertido

    @property
    def categoria(self) -> str:
        """Categoria normalizada (ex.: ``'Alimentação'``)."""
        return self.__categoria

    @categoria.setter
    def categoria(self, nova: str) -> None:
        if not isinstance(nova, str) or not nova.strip():
            raise ValorInvalidoError("A categoria não pode ser vazia.")
        self.__categoria = nova.strip().title()

    @property
    def data(self) -> date:
        """Data em que a transação ocorreu."""
        return self.__data

    @data.setter
    def data(self, nova: date | str) -> None:
        self.__data = parse_data(nova)

    @property
    def sujeita_a_orcamento(self) -> bool:
        """Indica se a transação consome o orçamento (padrão: não)."""
        return False

    @property
    def tipo(self) -> str:
        """Rótulo do tipo da transação (``'despesa'`` ou ``'receita'``)."""
        return self.TIPO

    # ------------------------------------------------------------------
    # Polimorfismo: contrato abstrato
    # ------------------------------------------------------------------
    @abstractmethod
    def aplicar(self, saldo: Decimal) -> Decimal:
        """Retorna o novo saldo após aplicar esta transação (não altera nada)."""

    @abstractmethod
    def get_resumo(self) -> str:
        """Retorna uma linha de texto legível descrevendo a transação."""

    @abstractmethod
    def _extras_dict(self) -> dict[str, Any]:
        """Campos específicos da subclasse a serem serializados."""

    @classmethod
    @abstractmethod
    def _extras_from_dict(cls, dados: dict[str, Any]) -> dict[str, Any]:
        """Extrai os campos específicos da subclasse a partir do dicionário."""

    # ------------------------------------------------------------------
    # Serialização
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Serializa a transação em um dicionário compatível com JSON."""
        return {
            "tipo": self.TIPO,
            "id": self.id,
            "descricao": self.descricao,
            "valor": str(self.valor),
            "categoria": self.categoria,
            "data": self.data.isoformat(),
            **self._extras_dict(),
        }

    @classmethod
    def from_dict(cls, dados: dict[str, Any]) -> "Transacao":
        """Reconstrói a subclasse correta a partir de um dicionário (factory).

        Raises:
            ValorInvalidoError: se o dicionário estiver incompleto ou o
                ``tipo`` for desconhecido.
        """
        try:
            alvo = cls._registro[dados["tipo"]]
            return alvo(
                descricao=dados["descricao"],
                valor=dados["valor"],
                categoria=dados["categoria"],
                data=dados["data"],
                id=dados["id"],
                **alvo._extras_from_dict(dados),
            )
        except KeyError as erro:
            raise ValorInvalidoError(
                f"Transação inválida no arquivo (campo ausente ou tipo desconhecido): {erro}"
            ) from erro

    def __str__(self) -> str:
        return self.get_resumo()

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id!r}, descricao={self.descricao!r}, "
            f"valor={self.valor}, categoria={self.categoria!r}, data={self.data})"
        )


class Despesa(Transacao):
    """Saída de dinheiro. Diminui o saldo e consome o orçamento da categoria."""

    TIPO: ClassVar[str] = "despesa"

    def __init__(
        self,
        descricao: str,
        valor: Decimal | float | int | str,
        categoria: str,
        data: date | str | None = None,
        id: str | None = None,  # noqa: A002
        forma_pagamento: str = "Não informada",
    ) -> None:
        super().__init__(descricao, valor, categoria, data, id)
        self.__forma_pagamento: str = (forma_pagamento or "Não informada").strip().title()

    @property
    def forma_pagamento(self) -> str:
        """Forma de pagamento (Dinheiro, Cartão, Pix...)."""
        return self.__forma_pagamento

    @property
    def sujeita_a_orcamento(self) -> bool:
        return True

    def aplicar(self, saldo: Decimal) -> Decimal:
        """Subtrai o valor da despesa do saldo."""
        return saldo - self.valor

    def get_resumo(self) -> str:
        return (
            f"[{self.id}] {formatar_data(self.data)} | DESPESA  | "
            f"{'-' + formatar_moeda(self.valor):>15} | {self.categoria} - "
            f"{self.descricao} ({self.forma_pagamento})"
        )

    def _extras_dict(self) -> dict[str, Any]:
        return {"forma_pagamento": self.forma_pagamento}

    @classmethod
    def _extras_from_dict(cls, dados: dict[str, Any]) -> dict[str, Any]:
        return {"forma_pagamento": dados.get("forma_pagamento", "Não informada")}


class Receita(Transacao):
    """Entrada de dinheiro. Aumenta o saldo e não consome orçamento."""

    TIPO: ClassVar[str] = "receita"

    def __init__(
        self,
        descricao: str,
        valor: Decimal | float | int | str,
        categoria: str,
        data: date | str | None = None,
        id: str | None = None,  # noqa: A002
        fonte: str = "Não informada",
    ) -> None:
        super().__init__(descricao, valor, categoria, data, id)
        self.__fonte: str = (fonte or "Não informada").strip().title()

    @property
    def fonte(self) -> str:
        """Origem da receita (Empregador, Cliente, Investimento...)."""
        return self.__fonte

    def aplicar(self, saldo: Decimal) -> Decimal:
        """Soma o valor da receita ao saldo."""
        return saldo + self.valor

    def get_resumo(self) -> str:
        return (
            f"[{self.id}] {formatar_data(self.data)} | RECEITA  | "
            f"{'+' + formatar_moeda(self.valor):>15} | {self.categoria} - "
            f"{self.descricao} (fonte: {self.fonte})"
        )

    def _extras_dict(self) -> dict[str, Any]:
        return {"fonte": self.fonte}

    @classmethod
    def _extras_from_dict(cls, dados: dict[str, Any]) -> dict[str, Any]:
        return {"fonte": dados.get("fonte", "Não informada")}
