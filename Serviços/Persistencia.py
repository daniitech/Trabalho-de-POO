"""Persistência da conta em arquivo JSON."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from models.conta_bancaria import ContaBancaria
from utils.excecoes import FinancasError, PersistenciaError


class RepositorioJSON:
    """Salva e carrega uma ``ContaBancaria`` em um arquivo JSON.

    A gravação é *atômica*: escreve em arquivo temporário e depois
    substitui o original, evitando corromper os dados se o programa cair
    no meio da escrita.
    """

    VERSAO_FORMATO: int = 1

    def __init__(self, caminho: str | Path = "data/dados.json") -> None:
        self.__caminho: Path = Path(caminho)

    @property
    def caminho(self) -> Path:
        """Caminho do arquivo de dados."""
        return self.__caminho

    def existe(self) -> bool:
        """Indica se já existe um arquivo salvo."""
        return self.__caminho.is_file()

    def salvar(self, conta: ContaBancaria) -> None:
        """Grava a conta no disco.

        Raises:
            PersistenciaError: em caso de erro de E/S.
        """
        conteudo = {"versao": self.VERSAO_FORMATO, "conta": conta.to_dict()}
        temporario: str | None = None
        try:
            self.__caminho.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.__caminho.parent, delete=False, suffix=".tmp"
            ) as arquivo:
                temporario = arquivo.name
                json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
            os.replace(temporario, self.__caminho)
        except OSError as erro:
            if temporario and os.path.exists(temporario):
                os.remove(temporario)
            raise PersistenciaError(f"Não foi possível salvar os dados: {erro}") from erro

    def carregar(self) -> ContaBancaria | None:
        """Lê a conta do disco.

        Returns:
            A conta carregada ou ``None`` se o arquivo ainda não existir.

        Raises:
            PersistenciaError: se o arquivo estiver corrompido ou ilegível.
        """
        if not self.existe():
            return None
        try:
            with self.__caminho.open(encoding="utf-8") as arquivo:
                conteudo = json.load(arquivo)
            return ContaBancaria.from_dict(conteudo["conta"])
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as erro:
            raise PersistenciaError(f"Arquivo de dados ilegível ou corrompido: {erro}") from erro
        except FinancasError as erro:
            raise PersistenciaError(f"Dados inválidos no arquivo: {erro}") from erro
