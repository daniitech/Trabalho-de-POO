# Diagrama de Classes UML

Sistema de Gestão Financeira Pessoal e Orçamento Doméstico.
Os diagramas usam sintaxe [Mermaid](https://mermaid.js.org/) e renderizam
diretamente no GitHub, GitLab, VS Code (extensão *Markdown Preview Mermaid*)
ou em <https://mermaid.live>.

**Notação de visibilidade:** `+` público · `-` privado (atributo `__x` do Python,
com *name mangling*) · `#` protegido (`_x`). Métodos abstratos terminam com `*`;
membros estáticos/de classe com `$`.

---

## 1. Diagrama principal (domínio, serviços e interface)

```mermaid
%%{init: {'theme':'neutral'}}%%
classDiagram
    direction TB

    class Transacao {
        <<abstract>>
        +TIPO: str$
        -__id: str
        -__descricao: str
        -__valor: Decimal
        -__categoria: str
        -__data: date
        +id: str
        +descricao: str
        +valor: Decimal
        +categoria: str
        +data: date
        +tipo: str
        +sujeita_a_orcamento: bool
        +aplicar(saldo: Decimal) Decimal*
        +get_resumo() str*
        #_extras_dict() dict*
        #_extras_from_dict(dados: dict) dict*
        +to_dict() dict
        +from_dict(dados: dict) Transacao$
        +__init_subclass__() None
    }

    class Despesa {
        +TIPO: str$
        -__forma_pagamento: str
        +forma_pagamento: str
        +sujeita_a_orcamento: bool
        +aplicar(saldo: Decimal) Decimal
        +get_resumo() str
    }

    class Receita {
        +TIPO: str$
        -__fonte: str
        +fonte: str
        +aplicar(saldo: Decimal) Decimal
        +get_resumo() str
    }

    class ContaBancaria {
        -__titular: str
        -__saldo_inicial: Decimal
        -__saldo: Decimal
        -__transacoes: list~Transacao~
        -__orcamento: Orcamento
        +titular: str
        +saldo: Decimal
        +saldo_inicial: Decimal
        +orcamento: Orcamento
        +transacoes: tuple~Transacao~
        +registrar_transacao(transacao: Transacao, ignorar_orcamento: bool) None
        +remover_transacao(id_transacao: str) Transacao
        +listar_transacoes(tipo, categoria, ano, mes) list~Transacao~
        +total_por_tipo(tipo: str, ano: int, mes: int) Decimal
        +gastos_por_categoria(ano: int, mes: int) dict
        +status_orcamento(ano: int, mes: int) list~StatusOrcamento~
        +resumo_mensal(ano: int, mes: int) dict
        +to_dict() dict
        +from_dict(dados: dict) ContaBancaria$
    }

    class Orcamento {
        +LIMIAR_ALERTA: Decimal$
        -__limites: dict
        +limites: Mapping
        +definir_limite(categoria: str, limite: Decimal) None
        +remover_limite(categoria: str) bool
        +obter_limite(categoria: str) Decimal
        +validar(despesa: Transacao, gasto_acumulado: Decimal) None
        +status(gastos_por_categoria: Mapping) list~StatusOrcamento~
        +to_dict() dict
        +from_dict(dados: Mapping) Orcamento$
    }

    class StatusOrcamento {
        <<dataclass frozen>>
        +categoria: str
        +limite: Decimal
        +gasto: Decimal
        +restante: Decimal
        +percentual: Decimal
        +situacao: str
    }

    class RepositorioJSON {
        +VERSAO_FORMATO: int$
        -__caminho: Path
        +caminho: Path
        +existe() bool
        +salvar(conta: ContaBancaria) None
        +carregar() ContaBancaria
    }

    class AplicacaoFinancas {
        -__repositorio: RepositorioJSON
        -__conta: ContaBancaria
        +executar() None
        -_registrar_receita() None
        -_registrar_despesa() None
        -_extrato() None
        -_remover() None
        -_menu_orcamento() None
        -_status_orcamento() None
        -_resumo_mensal() None
    }

    class Demonstracao {
        <<module services.demonstracao>>
        +executar_demonstracao() None$
        +popular_exemplo(conta: ContaBancaria) None$
    }

    %% Herança (generalização)
    Transacao <|-- Despesa : herda
    Transacao <|-- Receita : herda

    %% Composição: a conta é dona do histórico e do orçamento
    ContaBancaria "1" *-- "0..*" Transacao : historico
    ContaBancaria "1" *-- "1" Orcamento : orcamento

    %% Dependências
    Orcamento ..> Transacao : valida despesa
    Orcamento ..> StatusOrcamento : cria
    ContaBancaria ..> StatusOrcamento : retorna
    RepositorioJSON ..> ContaBancaria : salva / carrega
    Demonstracao ..> ContaBancaria : usa

    %% Associações da interface
    AplicacaoFinancas --> RepositorioJSON : persiste com
    AplicacaoFinancas --> ContaBancaria : opera sobre
    AplicacaoFinancas ..> Demonstracao : chama
```

---

## 2. Hierarquia de exceções de domínio

```mermaid
%%{init: {'theme':'neutral'}}%%
classDiagram
    direction TB

    class Exception {
        <<built-in>>
    }
    class FinancasError
    class ValorInvalidoError
    class SaldoInsuficienteError {
        +saldo_atual: Decimal
        +valor: Decimal
    }
    class LimiteOrcamentoExcedidoError {
        +categoria: str
        +limite: Decimal
        +gasto_projetado: Decimal
    }
    class TransacaoNaoEncontradaError
    class TransacaoDuplicadaError
    class PersistenciaError

    Exception <|-- FinancasError
    FinancasError <|-- ValorInvalidoError
    FinancasError <|-- SaldoInsuficienteError
    FinancasError <|-- LimiteOrcamentoExcedidoError
    FinancasError <|-- TransacaoNaoEncontradaError
    FinancasError <|-- TransacaoDuplicadaError
    FinancasError <|-- PersistenciaError

    ContaBancaria ..> SaldoInsuficienteError : lança
    ContaBancaria ..> TransacaoNaoEncontradaError : lança
    ContaBancaria ..> TransacaoDuplicadaError : lança
    Orcamento ..> LimiteOrcamentoExcedidoError : lança
    Transacao ..> ValorInvalidoError : lança
    RepositorioJSON ..> PersistenciaError : lança
```

---

## 3. Legenda: relação UML → conceito de POO

| Relação no diagrama | Onde aparece | Conceito de POO |
|---|---|---|
| `Transacao <\|-- Despesa / Receita` | herança | **Herança** e **Abstração** (`Transacao` é `ABC`, não instanciável) |
| `aplicar()` e `get_resumo()` (abstratos em `Transacao`, concretos nas filhas) | polimorfismo | **Polimorfismo** por sobrescrita: `ContaBancaria` chama `aplicar()` sem saber o tipo |
| `-__saldo`, `-__transacoes`, `-__limites` + `+saldo` (somente leitura) | atributos privados com *property* | **Encapsulamento**: o saldo só muda via `registrar_transacao` / `remover_transacao` |
| `ContaBancaria *-- Transacao` e `ContaBancaria *-- Orcamento` | losango preenchido | **Composição**: o ciclo de vida dos filhos depende da conta |
| `Orcamento ..> Transacao` | dependência | O orçamento valida limites por categoria recebendo a despesa como parâmetro |
| `Transacao.from_dict` + `__init_subclass__` | *factory* com registro automático | Extensibilidade (Aberto/Fechado): nova subclasse com `TIPO` é reconstruída sem alterar a base |
| `RepositorioJSON ..> ContaBancaria` | dependência | **Persistência** isolada em uma classe (responsabilidade única) |
| `AplicacaoFinancas --> RepositorioJSON / ContaBancaria` | associação | Separação entre interface (menu) e regras de negócio |
| `FinancasError` e derivadas | hierarquia de exceções | **Tratamento de exceções** com tipos próprios do domínio |
