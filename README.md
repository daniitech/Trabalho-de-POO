# Sistema de Gestão Financeira Pessoal e Orçamento Doméstico

Projeto Computacional 1 — POO em Python 3 (sem dependências externas).

## Estrutura
```
gestao_financeira/
├── main.py                  # menu interativo (AplicacaoFinancas)
├── models/
│   ├── transacao.py         # Transacao (ABC), Despesa, Receita
│   ├── conta_bancaria.py    # ContaBancaria (agrega Transacoes + Orcamento)
│   └── orcamento.py         # Orcamento e StatusOrcamento
├── services/
│   ├── persistencia.py      # RepositorioJSON
│   └── demonstracao.py      # roteiro automático para a defesa oral
├── utils/
│   ├── excecoes.py          # hierarquia de exceções de domínio
│   └── formatacao.py        # Decimal, moeda, datas
├── data/                    # dados.json é gerado aqui
├── tests/test_modelos.py    # testes automatizados
├── DIAGRAMA.md              # (ETAPA 4)
└── RELATORIO.md             # (ETAPA 5)
```

## Executar
```bash
python -m unittest discover -v   # testes
python main.py                   # menu interativo (salva em data/dados.json)
python main.py --demo            # demonstração automática dos conceitos de POO
```
