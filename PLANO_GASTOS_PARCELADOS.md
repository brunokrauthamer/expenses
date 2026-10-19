# Plano: cadastro de gastos parcelados no backend

Data: 18/10/2026. Backend implementado e migração aplicada ao PostgreSQL local.

## Objetivo

Permitir cadastrar um gasto à vista ou parcelado. No parcelamento, aceitar o valor total da compra ou o valor de cada parcela. A consulta mensal deve retornar somente as cobranças previstas para aquele mês, com o valor de cada parcela.

Exemplo: uma compra de R$ 1.200 em 6 parcelas, com primeira cobrança em novembro de 2026, aparece como R$ 200 em cada mês entre novembro de 2026 e abril de 2027.

## Decisões confirmadas com o usuário

- A primeira parcela pode ter uma data diferente da data da compra. Quando não informada, usar a data da compra.
- Editar ou excluir afeta o gasto inteiro e todas as parcelas, inclusive as de meses passados.

As regras de valor, calendário e consulta abaixo foram implementadas conforme as especificações deste plano. A API limita o cronograma a 1200 parcelas para evitar a criação de cobranças desproporcionais.

## Estado atual verificado

- O domínio fica em `backend/app/modules/expenses/`, separado em modelo, schemas, serviço e controller.
- `expenses.amount` guarda o total da compra e `expenses.expense_date` guarda sua data.
- `expense_installments` guarda valor, número e data de cada cobrança; `GET /expenses` filtra pelo vencimento e retorna uma linha por cobrança.
- Criação, PUT, exclusão, busca e paginação operam sobre o novo cronograma; mudanças de cronograma substituem as parcelas na mesma transação.
- Os 23 testes da API usam SQLite em memória com integridade referencial ativada. Ainda não validam a migração contra um servidor PostgreSQL.
- O frontend ainda não consome o backend, conforme `CONTEXTO.md`.
- A migração `20261018_0004` é o head do histórico e foi aplicada ao PostgreSQL local após confirmar que ele estava na revisão `20261018_0003`.

## Modelo de dados proposto

Manter um registro em `expenses` para a compra e criar `expense_installments` para suas cobranças. Um gasto à vista também terá uma cobrança, de número 1.

Essa estrutura permite filtrar, ordenar e paginar as cobranças diretamente no banco. Todas são geradas no cadastro; não é necessário executar uma tarefa a cada virada de mês.

### `expenses`

Preservar os campos atuais e acrescentar:

| Campo | Regra |
| --- | --- |
| `amount` | Sempre o valor total normalizado da compra, independentemente do modo de entrada. Preservar `NUMERIC(12,2)`. |
| `expense_date` | Data da compra. |
| `installment_count` | Quantidade de cobranças; de 1 a 1200, com 1 para gasto à vista. |
| `first_installment_date` | Data da primeira cobrança. Para gasto à vista, igual a `expense_date`. |

O tipo de pagamento pode ser derivado de `installment_count`: 1 significa à vista; 2 ou mais significa parcelado. Não é necessário persistir também um booleano que possa ficar inconsistente com a quantidade.

### `expense_installments`

| Campo | Regra |
| --- | --- |
| `id` | Chave primária. |
| `expense_id` | Referência obrigatória para `expenses`, com exclusão em cascata. |
| `installment_number` | Número da parcela, começando em 1. |
| `amount` | Valor positivo daquela cobrança, em `NUMERIC(12,2)`. |
| `due_date` | Data prevista da cobrança. |

Criar unicidade para `(expense_id, installment_number)`, índices para `due_date` e `expense_id`, e constraints para valores e números positivos. Descrição, categoria e meio de pagamento continuam no gasto principal.

Garantir no serviço que a quantidade de cobranças corresponda a `installment_count` e que sua soma corresponda a `expenses.amount`, dentro da mesma transação.

## Contrato de cadastro e edição

Preservar `description`, `amount`, `expense_date`, `category_id` e `payment_method_id`. Acrescentar:

| Campo | Regra proposta |
| --- | --- |
| `payment_type` | `one_time` ou `installments`; padrão `one_time` para manter os cadastros antigos válidos. Não confundir com `payment_method_id`, que indica PIX, cartão etc. |
| `installment_count` | Obrigatório e inteiro de 2 a 1200 quando parcelado. Para à vista, ausente ou 1. O limite evita cronogramas desproporcionais. |
| `amount_type` | `total` ou `installment`; padrão `total`. À vista aceita somente `total`. |
| `first_installment_date` | Opcional no parcelamento; padrão `expense_date`. Não pode ser anterior à compra. À vista aceita ausência ou a própria data da compra. |

Exemplo de `POST /expenses`:

```json
{
  "description": "Notebook",
  "amount": "1200.00",
  "amount_type": "total",
  "payment_type": "installments",
  "installment_count": 6,
  "expense_date": "2026-10-18",
  "first_installment_date": "2026-11-10",
  "category_id": 1,
  "payment_method_id": 2
}
```

Enviar `amount: "200.00"` e `amount_type: "installment"` deve gerar exatamente o mesmo cronograma e o mesmo total.

Regras monetárias:

- Usar `Decimal` ou centavos inteiros em todos os cálculos.
- Quando a entrada for o valor da parcela, multiplicar pela quantidade para obter o total.
- Quando a entrada for o total, dividir em centavos com arredondamento para baixo: `valor_das_demais = total // quantidade`; `primeira = total - (quantidade - 1) * valor_das_demais`. A primeira parcela recebe a diferença e todas as outras têm o mesmo valor. R$ 100,01 em 3 vezes gera R$ 33,35, R$ 33,33 e R$ 33,33; R$ 1.300 em 7 vezes gera R$ 185,74 e mais 6 parcelas de R$ 185,71.
- Rejeitar total que gere alguma parcela de valor zero, combinações contraditórias, números fracionários de parcelas, valores fora da precisão do banco e cronogramas fora do intervalo de datas suportado. Retornar HTTP 422.
- Não calcular juros automaticamente: o valor informado deve representar o total contratado ou a parcela contratada.

Regras de calendário:

- Gerar uma cobrança por mês, a partir de `first_installment_date`.
- Manter o dia original quando existir; caso contrário, usar o último dia do mês.
- Calcular cada vencimento a partir do dia original, evitando deslocamentos acumulados: 31/jan → 28/fev → 31/mar em ano não bissexto.

Na resposta de POST e PUT, expor `total_amount` com o total normalizado, `payment_type`, `installment_count`, `first_installment_date` e os dados do gasto. O modo de entrada não precisa ser persistido: para editar, o cliente pode usar o total retornado com `amount_type: "total"`.

## Consulta de leitura

Proposta: `GET /expenses` passa a listar cobranças, usando um schema próprio de leitura. Com `month`, filtrar `expense_installments.due_date`, em vez de `expenses.expense_date`.

Exemplo simplificado de item em `GET /expenses?month=2026-11`:

```json
{
  "id": 42,
  "installment_id": 101,
  "description": "Notebook",
  "expense_date": "2026-10-18",
  "due_date": "2026-11-10",
  "payment_type": "installments",
  "installment_number": 1,
  "installment_count": 6,
  "first_installment_date": "2026-11-10",
  "amount_due": "200.00",
  "total_amount": "1200.00",
  "category_id": 1,
  "payment_method_id": 2
}
```

- `id` continua sendo o ID do gasto, usado em PUT e DELETE. `installment_id` identifica a linha da cobrança.
- `amount_due` é o valor considerado no mês consultado. `total_amount` é apenas a informação do total da compra.
- Um gasto à vista aparece uma vez, com `installment_number: 1` e `installment_count: 1`.
- Fora do período das parcelas, o gasto não aparece no filtro mensal.
- Sem `month`, retornar todas as cobranças programadas, inclusive futuras, com a mesma estrutura. Nesse caso, um gasto parcelado aparece em várias linhas; cada uma tem `installment_id` próprio.
- Preservar a busca por descrição, categoria e meio de pagamento, além de `page`, `page_size`, `total` e `total_pages`.
- `total` passa a contar cobranças correspondentes aos filtros; continua sem representar soma monetária.
- Aplicar filtro, contagem, ordenação e paginação no banco. Ordenar por `due_date` decrescente e usar IDs como desempate estável.

Essa proposta altera deliberadamente o contrato de saída da listagem: substituir o campo genérico `amount` por `amount_due` e `total_amount`. Atualizar schemas, exemplos e testes para registrar a diferença. O formato das requisições antigas de cadastro continua aceito e representa gasto à vista.

## Edição e exclusão

- `PUT /expenses/{expense_id}` continua sendo uma edição completa do gasto. Permitir alterar valor, datas, quantidade e converter entre à vista e parcelado.
- Quando mudar o cronograma, recalcular e substituir todas as cobranças na mesma transação. Se mudar somente descrição, categoria ou meio de pagamento, preservar o cronograma.
- O ID do gasto permanece estável. IDs de parcelas recriadas podem mudar.
- `DELETE /expenses/{expense_id}` remove o gasto e todas as suas cobranças.
- Se a gravação falhar, desfazer toda a operação, preservando o estado anterior. Não deixar gasto sem cobranças nem parcelamento incompleto.

## Migração dos registros existentes

Criar uma nova migração após `20261018_0003`, sem reescrever o histórico:

1. Adicionar os novos campos ao gasto e criar `expense_installments`.
2. Para cada gasto existente, preencher `installment_count = 1` e `first_installment_date = expense_date`.
3. Inserir uma cobrança com número 1, o valor original e a data original.
4. Tornar os novos campos obrigatórios após o preenchimento e aplicar as constraints e índices.

Preservar IDs e valores dos gastos existentes. Antes de aplicar ao banco local, verificar a revisão atual e validar a migração em um PostgreSQL de teste, com banco vazio e com registros anteriores à mudança. Os testes SQLite existentes não substituem essa verificação.

## Arquivos implementados

- `backend/app/modules/expenses/model.py`: compra, cobrança e relacionamentos.
- `backend/app/modules/expenses/schema.py`: validação de entrada e respostas da API.
- `backend/app/modules/expenses/service.py` e `controller.py`: cronograma, CRUD e listagem mensal.
- `backend/migrations/versions/20261018_0004_add_expense_installments.py`: migração de dados legados e nova tabela.
- `backend/tests/`: fixtures com chaves estrangeiras e testes dos fluxos de parcelas.
- `backend/README.md` e `CONTEXTO.md`: contratos, limites e estado atualizado.

## Critérios de aceite e testes

- Cadastro antigo, sem campos novos, continua criando gasto à vista com uma cobrança.
- R$ 1.200 em 6 parcelas e R$ 200 por parcela em 6 vezes produzem o mesmo total e as mesmas cobranças.
- Cada consulta mensal retorna só a parcela daquele mês, incluindo a passagem de dezembro para janeiro e a última parcela.
- A compra não aparece antes da primeira cobrança nem após a última.
- Compra e primeira cobrança em meses diferentes funcionam corretamente.
- A soma das parcelas é exatamente o total, inclusive em divisões com resto de centavos.
- Datas nos dias 29, 30 e 31 respeitam meses curtos e anos bissextos, sem deslocar os meses seguintes.
- Combinações inválidas e totais fora dos limites retornam 422; referências inexistentes mantêm o comportamento 404.
- Busca e paginação continuam corretas com vários gastos e várias parcelas; sem filtro mensal, os identificadores de cobrança distinguem as linhas do mesmo gasto.
- Edição recalcula o conjunto completo, inclusive ao converter entre à vista e parcelado. Alterações só de descrição ou referências preservam as cobranças.
- Exclusão não deixa parcelas órfãs; garantir que o ambiente de teste realmente verifique a integridade referencial.
- Falha durante criação ou substituição de parcelas desfaz a operação inteira.
- A migração transforma gastos anteriores em cobranças únicas sem mudar seus IDs, valores e datas.

## Limites desta entrega

A implementação cobre o backend, seus testes, a documentação e o banco PostgreSQL local. Os 23 testes da suíte SQLite passaram; `alembic history` e `alembic current` confirmam `20261018_0004` como head e revisão aplicada. Uma consulta no PostgreSQL local confirmou que todos os gastos têm quantidade e soma de parcelas consistentes. A regra de divisão deixa as parcelas após a primeira iguais e arredondadas para baixo; a primeira recebe o restante. Integração com frontend, fechamento de fatura, controle de pagamento realizado, recorrência, juros calculados e edição individual de parcelas ficam fora deste escopo.
