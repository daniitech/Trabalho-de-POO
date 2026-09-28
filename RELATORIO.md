**Sistema de Gestão Financeira Pessoal e Orçamento Doméstico**

Projeto Computacional 1

Integrantes: Daniel Campos, Keven e Luiz Hamilton

Data de entrega: 28/09/2026

**1. Descrição**

Este projeto é um programa de terminal, escrito em Python 3, para controlar as finanças de uma pessoa. O usuário cria uma conta, registra receitas e despesas, define quanto pretende gastar por mês em cada categoria e acompanha o resultado do mês. Tudo é gravado em um arquivo JSON, então ao fechar e abrir o programa novamente os dados continuam lá.

O sistema foi construído seguindo os conceitos de Programação Orientada a Objetos vistos na disciplina. Existe uma classe abstrata chamada Transacao, com as subclasses Despesa e Receita. A classe ContaBancaria guarda o histórico de transações e o saldo, e a classe Orcamento verifica se uma despesa respeita o limite definido para a sua categoria.

**2. Justificativa**

Escolhemos este tema porque controle financeiro é algo do dia a dia e porque o assunto se encaixa bem na orientação a objetos. Conta, transação e orçamento são coisas que naturalmente viram classes, cada uma com seus dados e suas regras.

Além disso, o domínio pede cuidado com os dados. O saldo não pode ser alterado de qualquer jeito nem ficar negativo, o que justifica o uso de encapsulamento. Já o fato de uma despesa diminuir o saldo e uma receita aumentá-lo, tratados pela mesma chamada de método, é um bom exemplo de herança e polimorfismo.

Para os valores em dinheiro usamos a classe Decimal, em vez de float. Com float, contas simples como 0,1 + 0,2 não resultam exatamente em 0,3, e esse tipo de erro não é aceitável em um sistema financeiro.

**3. Funcionalidades**

Pelo menu do programa é possível registrar receitas e despesas, consultar o extrato com filtros por tipo, categoria e mês, remover transações e ver os dados da conta. Também é possível definir limites mensais por categoria, consultar a situação do orçamento e ver o resumo do mês, com total de receitas, total de despesas e o resultado.

Quando uma despesa ultrapassa o limite da categoria, o programa avisa e pergunta se o usuário quer registrar mesmo assim. O orçamento de cada categoria aparece como OK, ALERTA (a partir de 80% do limite) ou ESTOURADO. Ao remover uma transação, o saldo é recalculado, e a remoção é recusada se o saldo ficaria negativo.

Os dados são salvos automaticamente a cada alteração. Se o arquivo estiver corrompido, o programa guarda uma cópia dele com a extensão .corrompido.bak e começa uma conta nova. O menu ainda tem uma demonstração automática dos conceitos de POO, que não mexe nos dados reais, e uma opção para carregar dados de exemplo.

**4. Temas de POO abordados**

**Abstração e herança.** A classe Transacao herda de ABC, portanto não pode ser instanciada diretamente. Ela reúne o que é comum a qualquer movimentação (identificador, descrição, valor, categoria e data) e declara os métodos abstratos que as filhas precisam implementar. Despesa acrescenta a forma de pagamento e Receita acrescenta a fonte do dinheiro.

**Polimorfismo.** Os métodos aplicar() e get_resumo() são declarados na classe base e sobrescritos nas subclasses. A ContaBancaria chama aplicar() sem saber se a transação é uma despesa ou uma receita:

    novo_saldo = transacao.aplicar(self.__saldo)

Na Despesa o método devolve saldo menos valor, e na Receita devolve saldo mais valor. O extrato funciona do mesmo jeito, pois cada classe monta a sua própria linha em get_resumo(). Usamos também a propriedade sujeita_a_orcamento, que é verdadeira para despesas, para evitar verificações de tipo com isinstance dentro da conta.

**Encapsulamento.** Os atributos importantes são privados, com dois underlines no início do nome, e só são acessados por properties. O saldo da conta não tem setter: ele muda apenas pelos métodos registrar_transacao e remover_transacao, o que garante que o saldo seja sempre o saldo inicial somado ao efeito de todas as transações. Os setters validam os dados, por exemplo:

    if convertido <= 0:
        raise ValorInvalidoError("O valor da transação deve ser positivo.")

O histórico é devolvido como tupla, para que quem consulta não consiga alterar a lista interna. Se alguém tentar fazer conta.saldo = 999, o Python lança um AttributeError.

**Composição.** A ContaBancaria é dona da lista de transações e do seu Orcamento, que nascem, são salvos e são carregados junto com ela. Na hora de registrar uma despesa, a conta calcula quanto já foi gasto na categoria naquele mês e entrega esse valor ao orçamento, que decide se o limite seria ultrapassado. Assim cada classe fica com uma responsabilidade só.

**Persistência em JSON.** A classe RepositorioJSON é responsável por ler e gravar o arquivo. Cada classe do modelo tem os métodos to_dict e from_dict para converter seus dados. A gravação é feita primeiro em um arquivo temporário, que depois substitui o original, para não perder dados caso o programa seja interrompido no meio. Os valores em dinheiro são gravados como texto para não perder precisão, e ao carregar o arquivo o saldo é recalculado a partir do histórico.

**Fábrica de objetos.** O método Transacao.from_dict descobre pelo campo tipo do JSON qual subclasse deve criar. As subclasses se registram sozinhas usando __init_subclass__, então um novo tipo de transação poderia ser adicionado sem alterar a classe base.

**Tratamento de exceções.** Criamos uma hierarquia própria de erros, a partir de FinancasError. Ela inclui ValorInvalidoError, SaldoInsuficienteError, LimiteOrcamentoExcedidoError, TransacaoNaoEncontradaError, TransacaoDuplicadaError e PersistenciaError. O menu captura FinancasError e mostra uma mensagem clara ao usuário, sem esconder erros de programação.

Todo o código usa type hints e docstrings, e os testes automatizados (24 casos, com unittest) cobrem os principais comportamentos das classes e da persistência.

**5. Tecnologias e bibliotecas**

Usamos apenas a biblioteca padrão do Python 3, então não é preciso instalar nada. Os módulos principais foram abc (classe abstrata), decimal (valores monetários), datetime (datas), json (persistência), pathlib, os e tempfile (arquivos e gravação segura), dataclasses e typing (objetos imutáveis e anotações de tipo), uuid (identificadores) e unittest (testes). O controle de versão foi feito com Git e o diagrama de classes foi escrito em Mermaid.

**6. Organização do repositório**

O arquivo main.py contém o menu interativo. A pasta models tem transacao.py, conta_bancaria.py e orcamento.py. A pasta services tem persistencia.py e demonstracao.py. A pasta utils tem excecoes.py e formatacao.py. Os testes ficam em tests/test_modelos.py, o arquivo de dados é criado em data/dados.json durante o uso, e a documentação está em README.md, DIAGRAMA.md e RELATORIO.md.

**7. Como executar**

Na pasta do projeto, os testes rodam com python -m unittest discover -v, o menu interativo abre com python main.py e a demonstração automática com python main.py --demo.

**8. Distribuição de tarefas**

Daniel Campos ficou com a hierarquia de transações (Transacao, Despesa e Receita), a fábrica de objetos, as funções de formatação e os testes dessa parte.

Keven ficou com a ContaBancaria e o Orcamento, as regras de saldo e de limites, a hierarquia de exceções, os testes correspondentes e o diagrama de classes.

Luiz Hamilton ficou com a persistência em JSON, o menu interativo, a demonstração automática, o README, o relatório e a organização do repositório no Git.

A revisão do código, os testes manuais e a preparação da apresentação foram feitos pelos três em conjunto.

**9. Conclusão**

O sistema atende aos requisitos da disciplina: encapsulamento, herança com classe abstrata, polimorfismo, composição e persistência de dados, com tratamento de exceções, testes automatizados e documentação. Por ser dividido em camadas, o projeto pode crescer com facilidade, por exemplo com novos tipos de transação, novos relatórios ou uma interface gráfica, sem reescrever as classes do domínio.
