# Plano: entradas, salários e reembolsos

Data: 22/10/2026. Este é um plano de evolução; não há alteração de banco, API ou interface nesta etapa.

## Objetivo

Além de despesas, permitir registrar valores que entram. A primeira versão terá as categorias de entrada **Salário** e **Reembolso**; outras, como **Bônus**, poderão ser acrescentadas depois.

Um reembolso não deve parecer uma nova despesa nem uma receita comum: ele reduz o custo de uma categoria de gasto. Por isso, toda entrada na categoria Reembolso deve obrigatoriamente indicar a categoria de despesa a que se refere.

Exemplo: para um churrasco, registrar uma despesa de R$ 600,00 em Mercado e dois reembolsos de R$ 200,00 também vinculados a Mercado. No consolidado do período, Mercado deve apresentar R$ 600,00 de gasto bruto, R$ 400,00 de reembolsos e R$ 200,00 de gasto líquido.

## Decisões propostas

- Preservar despesas e suas parcelas exatamente como funcionam hoje. O valor de uma compra continua sendo positivo e o seu cronograma continua representando cobranças previstas.
- Criar um domínio próprio para entradas. Não usar valores negativos em `expenses` nem criar uma categoria de despesa chamada “Reembolso”; essas alternativas distorceriam a lista de compras, os filtros e o futuro balanço financeiro.
- A data de uma entrada será a data em que o dinheiro foi recebido. Para que o exemplo do churrasco apareça como R$ 200,00 no mesmo consolidado mensal, os dois reembolsos devem ser cadastrados no mesmo mês da cobrança de R$ 600,00.
- O consolidado de gastos passará a distinguir gasto bruto, reembolso e gasto líquido. Os gráficos e o destaque principal usarão o valor líquido; o bruto e os reembolsos ficarão visíveis para a conta ser auditável.
- Salário, bônus e demais entradas reais serão mostrados separadamente dos gastos. Eles não diminuem nenhuma categoria de despesa.
- Nesta primeira entrega, reembolso exige a **categoria de despesa**, mas não uma despesa específica. A ligação opcional a uma compra poderá ser uma evolução posterior, se for necessário conciliar cada devolução com um evento ou uma compra parcelada.

## Modelo de dados

Criar o módulo `income_entries` (nome da interface: **Entradas**) e duas tabelas novas.

### `income_categories`

| Campo | Regra |
| --- | --- |
| `id` | Chave primária. |
| `name` | Nome único, até 50 caracteres. Exemplos iniciais: Salário e Reembolso. |
| `requires_expense_category` | Booleano. `true` para Reembolso; `false` para Salário, Bônus e entradas normais. |

O seeder cria Salário (`false`) e Reembolso (`true`) sem duplicar categorias já existentes. Uma futura tela de categorias poderá adicionar Bônus sem mudar o modelo.

### `income_entries`

| Campo | Regra |
| --- | --- |
| `id` | Chave primária. |
| `description` | Obrigatória, até 120 caracteres. Ex.: “Salário de outubro” ou “Reembolso do João — churrasco”. |
| `amount` | `NUMERIC(12,2)` positivo. |
| `received_date` | Data em que o valor entrou. |
| `income_category_id` | Categoria da entrada, obrigatória; referência para `income_categories`. |
| `expense_category_id` | Referência opcional para `categories`, mas obrigatória quando a categoria de entrada exigir vínculo com gasto. |
| `created_at` | Data e hora de criação, com fuso. |

As chaves estrangeiras usarão `RESTRICT`: uma categoria usada por uma entrada não poderá ser apagada inadvertidamente. Criar índices para `received_date`, `income_category_id` e `expense_category_id`.

A constraint de banco garantirá valor positivo. A regra condicional do reembolso será validada no serviço: se `requires_expense_category` for verdadeiro, a categoria de despesa é obrigatória; se for falso, ela deve ficar vazia. Isso evita depender do nome ou do ID fixo da categoria “Reembolso”.

## API proposta

Novo prefixo: `/income-entries`.

- `GET /income-categories`: devolve as categorias de entrada.
- `GET /income-entries`: lista entradas paginadas, com filtros opcionais de período, categoria de entrada, categoria de despesa e busca.
- `POST /income-entries`: cria uma entrada.
- `PUT /income-entries/{id}`: substitui uma entrada.
- `DELETE /income-entries/{id}`: remove uma entrada.

Exemplo de salário:

```json
{
  "description": "Salário de outubro",
  "amount": "8500.00",
  "received_date": "2026-10-05",
  "income_category_id": 1
}
```

Exemplo de reembolso de R$ 200,00 para Mercado:

```json
{
  "description": "Reembolso da Ana — churrasco",
  "amount": "200.00",
  "received_date": "2026-10-22",
  "income_category_id": 2,
  "expense_category_id": 1
}
```

Os contratos de despesas existentes permanecem compatíveis. A API deve responder `422` para valor não positivo, descrição vazia, categoria inexistente, reembolso sem categoria de despesa ou entrada comum com categoria de despesa preenchida.

## Cálculo do gasto líquido

O atual `GET /expenses/summary` soma parcelas por vencimento. Ele deve evoluir de modo explícito, sem ocultar os valores originais:

```json
{
  "gross_expense_amount": "600.00",
  "reimbursement_amount": "400.00",
  "net_expense_amount": "200.00",
  "monthly_totals": [
    {
      "month": "2026-10",
      "gross_expense_amount": "600.00",
      "reimbursement_amount": "400.00",
      "net_expense_amount": "200.00"
    }
  ],
  "category_totals": [
    {
      "category_id": 1,
      "gross_expense_amount": "600.00",
      "reimbursement_amount": "400.00",
      "net_expense_amount": "200.00"
    }
  ]
}
```

Para cada mês e categoria:

```text
gasto líquido = parcelas com vencimento no período − reembolsos recebidos no período
```

Os cálculos continuarão usando `Decimal` (ou centavos inteiros), nunca `float`.

Essa definição mantém o sentido atual de “cobrança prevista” para despesas e registra o reembolso quando ele de fato entra. Se uma pessoa devolver o dinheiro no mês seguinte, outubro exibirá o gasto bruto e novembro exibirá o reembolso daquela categoria. Essa transparência é essencial para o futuro fluxo de caixa e balanço. Para analisar uma ocasião independentemente da data de recebimento, será necessária a futura ligação direta do reembolso a uma despesa.

O filtro por categoria deve incluir tanto as parcelas quanto os reembolsos dessa categoria. O filtro por meio de pagamento continuará dizendo respeito apenas às despesas, pois entradas ainda não terão conta ou meio de recebimento; a interface deverá explicar isso ou desabilitar esse filtro no recorte líquido para evitar interpretação ambígua.

## Interface proposta

Manter a tela `/despesas` e incluir, acima do formulário, um seletor simples:

- **Despesa**: preserva o formulário atual, inclusive parcelamento e meio de pagamento.
- **Entrada**: mostra descrição, valor, data de recebimento e categoria de entrada.

Ao selecionar Reembolso, exibir também “Categoria do gasto reembolsado”, obrigatória, usando as categorias de despesas existentes. Não exibir meio de pagamento ou parcelamento para entradas nesta fase.

A lista mensal pode continuar dedicada às cobranças. Em uma seção ou tela de Entradas, listar salário e reembolsos recebidos no mês, com uma identificação clara da categoria de gasto no caso de reembolso. Isso evita misturar uma compra com a devolução recebida.

No consolidado, substituir o único “Total das cobranças” por três números claros: **gastos brutos**, **reembolsos** e **gasto líquido**. O título e o rodapé devem deixar claro que o resultado é calculado por vencimento das parcelas e data de recebimento dos reembolsos.

## Futuro balanço e investimentos

O cadastro de entradas preparado acima é a base, mas não é ainda um balanço financeiro. Quando esse recurso for iniciado, criar um relatório próprio que combine:

```text
Entradas reais (salário, bônus, etc.)
− despesas/cobranças
+ reembolsos
= resultado do período
```

Reembolsos não devem ser subtraídos duas vezes: no relatório de categorias, reduzem o gasto; no fluxo de caixa, são uma entrada de dinheiro. O relatório precisará apresentar essas duas perspectivas em áreas diferentes, com rótulos claros.

Investimentos devem ser outro domínio, separado de categorias de despesas e entradas. Antes de implementá-los, será preciso decidir se a tela registra aportes, posição atual, rentabilidade, contas/carteiras e importação de dados. Não antecipar esses campos agora evita um modelo difícil de corrigir depois.

## Etapas de implementação

1. Criar modelos, schemas, serviços, controllers e migração Alembic após `20261019_0005` para categorias e entradas; atualizar o seeder e o registro de módulos.
2. Cobrir o CRUD e as regras de reembolso com testes de API, incluindo chaves estrangeiras e precisão monetária.
3. Estender o resumo para devolver bruto, reembolso e líquido por mês e categoria; testar o churrasco de R$ 600,00 com dois reembolsos de R$ 200,00 e datas em meses diferentes.
4. Atualizar o formulário, cliente HTTP, caches e telas responsivas. Invalidar tanto o consolidado quanto a lista de entradas após criar, editar ou excluir uma entrada.
5. Executar a suíte backend, gerar o build do frontend, aplicar a migração em PostgreSQL local após conferir a revisão atual e validar o fluxo no navegador em desktop e celular.
6. Atualizar `CONTEXTO.md` com a decisão efetivamente implementada, a nova migração e os resultados dos testes.

## Critérios de aceite

- Salário pode ser cadastrado sem categoria de despesa.
- Reembolso sem categoria de despesa é rejeitado; com uma categoria válida, é aceito.
- A despesa de Mercado de R$ 600,00 e dois reembolsos de R$ 200,00 produzem R$ 600,00 bruto, R$ 400,00 reembolsado e R$ 200,00 líquido na categoria Mercado, quando as datas pertencem ao mesmo recorte.
- Um reembolso de outra categoria não altera Mercado.
- Editar ou excluir um reembolso recalcula o consolidado sem recarregar a página.
- Parcelamentos seguem aparecendo pelo vencimento de cada parcela; nenhum registro existente é alterado pela migração.
- Valores de salário e outros ganhos não reduzem categorias de despesas.
- A interface informa com clareza o que é gasto bruto, reembolso e gasto líquido, mantém teclado, foco, contraste e comportamento adequado em celular.

## Fora do escopo inicial

- Recorrência automática de salário.
- Contas bancárias, saldo disponível, conciliação de extratos e confirmação de recebimento/pagamento.
- Vínculo obrigatório entre reembolso e uma despesa específica, rateio de reembolso entre parcelas ou pessoas.
- Investimentos, patrimônio, rentabilidade e metas.
- Importação de entradas.

