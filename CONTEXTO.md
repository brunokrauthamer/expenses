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

O backend possui uma API de despesas e estrutura de banco separada. Os routers de categorias e meios de pagamento existem, mas ainda não possuem rotas implementadas. Não há seed de categorias ou meios de pagamento nas migrações. O usuário deseja que as categorias do dropdown venham do banco futuramente.

### API de despesas

- `GET /expenses`: paginação por `page` (padrão 1) e `page_size` (padrão 20, máximo 100); filtros opcionais `month` no formato `AAAA-MM` e `search`. A busca procura descrição, nome da categoria e nome do meio de pagamento, sem diferenciar maiúsculas de minúsculas.
- `POST /expenses`: cria uma despesa.
- `PUT /expenses/{expense_id}`: atualiza a despesa com todos os campos exigidos na criação.
- `DELETE /expenses/{expense_id}`: exclui e retorna HTTP 204.

Na criação e edição, enviar `description`, `amount`, `expense_date`, `category_id` e `payment_method_id`. O valor deve ser positivo e as referências devem existir. A listagem retorna `items`, `page`, `page_size`, `total` e `total_pages`; `total` é a quantidade de registros, não a soma dos valores. A documentação interativa do FastAPI fica em `/docs` quando o servidor está em execução.

## Banco de dados

O banco escolhido é PostgreSQL local; o usuário instalou o PostgreSQL e usa o pgAdmin para inspecioná-lo. A configuração fica em `backend/.env`, com `DATABASE_URL`; há um modelo em `backend/.env.example`. Não copiar credenciais para documentação, commits ou respostas.

Tabelas definidas pelo código e migrações:

- `categories`: `id` BIGINT e `name` VARCHAR(50), obrigatório e único.
- `payment_methods`: `id` INTEGER e `name` VARCHAR(50), obrigatório e único.
- `expenses`: `id` BIGINT, `description` VARCHAR(120), `amount` NUMERIC(12,2) positivo, `expense_date` DATE, `category_id` BIGINT, `payment_method_id` INTEGER e `created_at` com fuso horário. As duas referências são obrigatórias e usam chaves estrangeiras com restrição de exclusão.

As migrações são `20261017_0001` (categorias e despesas), `20261018_0002` (meios de pagamento e referência) e `20261018_0003` (IDs de meios de pagamento como INTEGER). Antes de aplicar em um banco com dados existentes, inspecione a migração 0002: ela adiciona uma coluna obrigatória sem preencher despesas já existentes. Confirme a revisão efetivamente aplicada no banco antes de declarar seu estado. O README do backend está parcialmente desatualizado quanto aos módulos e tabelas.

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

Os testes usam SQLite em memória, não o PostgreSQL local. Em uma execução anterior foram relatados 6 testes aprovados e 83% de cobertura; esses números são históricos, não uma garantia do estado atual. O frontend não declara script de testes em `package.json`.

## Git e GitHub

Frontend e backend ficam no mesmo repositório Git. O repositório GitHub `brunokrauthamer/expenses` foi criado pelo usuário e o remoto `origin` aponta para `https://github.com/brunokrauthamer/expenses.git`. A branch atual é `master`, configurada para acompanhar `origin/master`. O commit inicial foi criado e enviado: `65e1b5c` (`Initial commit`).

A identidade usada no commit veio do perfil GitHub conectado: Bruno Krauthamer (`brunokrauthamer@gmail.com`). Ela foi configurada localmente neste repositório. Futuras melhorias devem usar branches separadas e PRs para `master`; não há necessidade atual de branches principais `dev`, `qa` ou `staging`.

O primeiro push falhou sob a rede restrita do ambiente e foi concluído após autorização de rede. Se um push futuro falhar por conectividade, verificar a rede/autenticação GitHub e repetir com o acesso apropriado. A integração GitHub disponível no chat pode consultar recursos, mas não oferece criação de repositórios. Navegador e GitHub CLI não estavam disponíveis naquela sessão.

Antes de qualquer commit, revise os arquivos staged e assegure que segredos, ambiente virtual, dependências instaladas e arquivos gerados permanecem excluídos. O `.gitignore` cobre `.env`, ambientes virtuais, `node_modules`, builds, caches Python e cobertura.

