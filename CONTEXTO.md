# Contexto do projeto Expenses

Atualizado em 18/10/2026. Este documento resume decisões e o estado observado. Em novos chats, confira o código, o Git e as migrações antes de assumir que nada mudou.

## Objetivo e preferências

Aplicação web simples de controle de despesas pessoais. O usuário está desenvolvendo seu primeiro software com ajuda de um agente de programação e prefere explicações claras. Priorizar ferramentas gratuitas, evitar serviços pagos e não acrescentar funcionalidades sem solicitação. Não expor segredos nem executar comandos destrutivos sem autorização. O usuário solicitou execução dos testes disponíveis e correção de erros ao implementar mudanças.

A interface deve ser simples, responsiva e agradável, com visual moderno, cores leves, transições e animações suaves. A cor verde está proibida. Usar nomes em inglês para tabelas e colunas do banco.

## Organização

O projeto fica em `C:\Users\bruno\Documents\ChatGPT\expenses` e reúne frontend e backend no mesmo repositório:

```text
expenses/
  frontend/               React, Vite e CSS
    src/App.jsx           Interface e lógica atual
    src/main.jsx          Entrada do React
    src/styles.css        Estilos e responsividade
  backend/                FastAPI, SQLAlchemy, Alembic e PostgreSQL
    app/config.py         Leitura de configuração
    app/database.py       Engine, sessão e base do SQLAlchemy
    app/main.py           Aplicação e registro das rotas
    app/modules/          Domínios categories, expenses e payment_methods
    app/shared/           Dependências e exceções compartilhadas
    migrations/           Migrações Alembic
    tests/                Testes da API
  .gitignore
```

O backend segue um monólito modular. Cada domínio tem arquivos `model.py`, `schema.py`, `service.py` e `controller.py`: modelos de banco, contratos da API, regras/consultas e rotas HTTP, respectivamente. A separação por domínio procura facilitar reaproveitamento futuro, sem assumir que já existam microsserviços.

## Estado funcional

O frontend permite cadastrar descrição, valor, categoria e data, listar e excluir despesas e calcular o total. Usa estado React em memória: os dados são perdidos ao recarregar a página. As categorias estão definidas diretamente em `App.jsx`. O frontend ainda não se comunica com o backend, não oferece meio de pagamento, edição, filtro por mês nem busca.

O backend possui uma API de despesas e estrutura de banco separada. Os routers de categorias e meios de pagamento existem, mas ainda não possuem rotas implementadas. Não há seed de categorias ou meios de pagamento nas migrações. O usuário deseja que as categorias do dropdown venham do banco futuramente. A API de despesas também gera e consulta cobranças de gastos parcelados.

### API de despesas

- `GET /expenses`: lista cobranças paginadas (`page` padrão 1, `page_size` padrão 20 e máximo 100). `month` no formato `AAAA-MM` filtra pela data da cobrança; sem filtro, retorna todas as cobranças programadas. `search` procura descrição, nome da categoria e nome do meio de pagamento sem diferenciar maiúsculas de minúsculas.
- `POST /expenses`: cria uma compra à vista ou parcelada e gera suas cobranças.
- `PUT /expenses/{expense_id}`: substitui os dados do gasto; altera o cronograma inteiro quando muda valor, datas ou quantidade.
- `DELETE /expenses/{expense_id}`: exclui o gasto e suas cobranças; retorna HTTP 204.

Na criação e edição, enviar `description`, `amount`, `expense_date`, `category_id` e `payment_method_id`. `payment_type` aceita `one_time` (padrão) ou `installments`; `installment_count` aceita de 1 a 1200 e exige ao menos 2 para parcelados; `amount_type` aceita `total` (padrão) ou `installment`; `first_installment_date` é opcional e usa `expense_date` como padrão. Em parcelamentos, `amount` pode representar o total ou o valor de cada parcela conforme `amount_type`. A resposta mensal usa `amount_due` para a cobrança do mês e `total_amount` para o total da compra. O `id` representa o gasto e `installment_id` representa uma cobrança. `total` conta cobranças, nunca soma valores. A documentação interativa do FastAPI fica em `/docs` quando o servidor está em execução.

## Banco de dados

O banco escolhido é PostgreSQL local; o usuário instalou o PostgreSQL e usa o pgAdmin para inspecioná-lo. A configuração fica em `backend/.env`, com `DATABASE_URL`; há um modelo em `backend/.env.example`. Não copiar credenciais para documentação, commits ou respostas.

Tabelas definidas pelo código e migrações:

- `categories`: `id` BIGINT e `name` VARCHAR(50), obrigatório e único.
- `payment_methods`: `id` INTEGER e `name` VARCHAR(50), obrigatório e único.
- `expenses`: `id` BIGINT, `description` VARCHAR(120), `amount` NUMERIC(12,2) positivo (total da compra), `expense_date` DATE, `installment_count` INTEGER, `first_installment_date` DATE, `category_id` BIGINT, `payment_method_id` INTEGER e `created_at` com fuso horário. As referências são obrigatórias e usam chaves estrangeiras com restrição de exclusão.
- `expense_installments`: `id` BIGINT, `expense_id` BIGINT (exclusão em cascata), `installment_number` INTEGER, `amount` NUMERIC(12,2) positivo e `due_date` DATE. Cada compra tem ao menos uma cobrança; o par `(expense_id, installment_number)` é único.

As migrações do código e do PostgreSQL local terminam em `20261018_0004` (`expense_installments` e campos do cronograma). Ela foi aplicada partindo de `20261018_0003` e converte cada gasto preexistente em uma cobrança única. Uma verificação posterior não encontrou gastos com soma ou quantidade de parcelas inconsistente.

## Execução local

No frontend, a partir de `frontend`, com Node.js 20.19+ ou 22.12+ e pnpm:

```powershell
pnpm install
pnpm dev
```

Abrir o endereço informado pelo Vite, normalmente `http://localhost:5173`. Para gerar o build: `pnpm build`.

No backend, a partir de `backend`, com Python e PostgreSQL configurados:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
# Copiar .env.example para .env e configurar DATABASE_URL localmente.
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Há um ambiente virtual local em `backend/.venv` na máquina do usuário; ele e o arquivo `.env` são ignorados pelo Git. Criar ou recriar o ambiente apenas quando necessário.

Para os testes do backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```

Os testes usam SQLite em memória, não o PostgreSQL local. Após a implementação dos parcelamentos, 23 testes do backend passaram. A migração Alembic foi aplicada ao PostgreSQL local e `20261018_0004` foi confirmado como revisão atual. O frontend não declara script de testes em `package.json`.

## Git e GitHub

Frontend e backend ficam no mesmo repositório Git. O repositório GitHub `brunokrauthamer/expenses` foi criado pelo usuário e o remoto `origin` aponta para `https://github.com/brunokrauthamer/expenses.git`. A branch atual é `master`, configurada para acompanhar `origin/master`. O commit inicial foi criado e enviado: `65e1b5c` (`Initial commit`).

A identidade usada no commit veio do perfil GitHub conectado: Bruno Krauthamer (`brunokrauthamer@gmail.com`). Ela foi configurada localmente neste repositório. Futuras melhorias devem usar branches separadas e PRs para `master`; não há necessidade atual de branches principais `dev`, `qa` ou `staging`.

O primeiro push falhou sob a rede restrita do ambiente e foi concluído após autorização de rede. Se um push futuro falhar por conectividade, verificar a rede/autenticação GitHub e repetir com o acesso apropriado. A integração GitHub disponível no chat pode consultar recursos, mas não oferece criação de repositórios. Navegador e GitHub CLI não estavam disponíveis naquela sessão.

Antes de qualquer commit, revise os arquivos staged e assegure que segredos, ambiente virtual, dependências instaladas e arquivos gerados permanecem excluídos. O `.gitignore` cobre `.env`, ambientes virtuais, `node_modules`, builds, caches Python e cobertura.

