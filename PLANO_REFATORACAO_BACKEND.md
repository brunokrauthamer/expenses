# Plano de refatoração do backend

Data de execução: 24/10/2026.

Status: refatoração implementada na branch `backend-refactor`. A separação de responsabilidades foi concluída sem mudança de esquema, migrations ou comportamento intencional da API. Os resultados e limites verificados estão na seção 6.

Diretrizes gerais: [AGENTS.md](AGENTS.md).

Comandos e comportamentos da API: [backend/README.md](backend/README.md).

## 1. Arquitetura implementada

O Expenses continua como monólito modular por domínio. Controllers adaptam HTTP; services implementam casos de uso e regras; repositories concentram consultas e gravações; models declaram entidades; schemas definem contratos da API. A composição cria services com adaptadores de persistência e `UnitOfWork`.

```text
backend/app/modules/<dominio>/
  controller.py       # HTTP, autenticação da rota e mapeamento de erros/respostas
  schema.py           # contratos externos da API
  service.py          # regras, validações de domínio e coordenação dos casos de uso
  model.py            # mapeamentos ORM
  repository.py       # consultas e gravações SQLAlchemy, quando necessárias
  dependencies.py     # composição de dependências do domínio
  contracts.py        # comandos, snapshots e resultados internos, quando necessários
  rules.py            # regras puras do domínio, quando necessárias
```

Os arquivos opcionais só aparecem onde há responsabilidade correspondente. Os services usam contratos pequenos de repositório e `UnitOfWork`, sem FastAPI, SQLAlchemy, schemas HTTP ou objetos de requisição. Controllers recebem UUID da conta autenticada e não manipulam `Session` nem entidades ORM. Repositórios não importam services e fazem `flush`, sem commit próprio.

`shared/transactions.py` define o contrato de transação e `atomic()`; `shared/sqlalchemy_uow.py` fornece a implementação SQLAlchemy. Cada operação de escrita confirma uma vez ou restaura a sessão no rollback. A autenticação confirma explicitamente a revogação de uma família/sessão de refresh antes de devolver recusa de autenticação quando a política de segurança exige esse efeito.

A autenticação agora separa persistência (`auth/repository.py`), casos de uso (`auth/service.py`), transporte e validação do provedor Google (`auth/oauth.py`), tokens (`auth/tokens.py`) e dependências HTTP (`auth/dependencies.py`). PKCE, `state`, `nonce`, validação de ID token, restrição de retorno a rotas internas, cookies HttpOnly e vínculo Google controlado por domínio foram preservados.

O engine SQLAlchemy é criado sob demanda em `app/database.py`. Importar regras ou serviços não inicializa conexão nem exige carregar credenciais. As dependências FastAPI compõem os casos de uso quando a aplicação recebe uma requisição.

## 2. Escopo implementado e comportamentos preservados

- Categorias, categorias de entrada e meios de pagamento têm serviços por domínio; a persistência comum de catálogos fica em um adaptador compartilhado. Normalização e unicidade de nomes ativos, exclusão lógica e regra imutável de categoria de reembolso após o primeiro uso permanecem no caso de uso apropriado.
- Despesas e entradas recebem comandos internos independentes dos schemas HTTP. Regras de período continuam compartilhadas sem uniformizar as mensagens distintas de despesa e entrada. Cronogramas preservam centavos, resto na primeira parcela, limite de 1.200 parcelas e vencimentos no fim do mês.
- Consultas de listagem, histórico, paginação, resumo e relações continuam no repositório, mantendo escopo por conta e agregações financeiras. O service de despesas combina cobranças e reembolsos com `Decimal`; meio de pagamento exclui reembolsos do resumo, e aliases de valor líquido continuam na resposta.
- A associação de reembolsos preserva referências históricas excluídas ao editar e exige categoria de despesa conforme `requires_expense_category`. Salários e demais ganhos continuam fora do cálculo de despesas.
- Seeder e cadastro/login compartilham a inicialização transacional e única dos catálogos. A prévia e o `--apply` do importador foram mantidos; o service exige proprietário, preserva valores observados, recusa importação parcialmente duplicada e grava a aplicação em uma transação.
- Contratos HTTP, status, autenticação, autorização por proprietário, constraints de propriedade e regras financeiras foram preservados pelos testes de API existentes. Não foram acrescentados recursos nem alterado o esquema.

Os arquivos antigos `shared/auth.py` e `shared/catalog.py`, que misturavam transporte, regras ou persistência, foram removidos após mover seus consumidores. A inicialização de `shared/reference_data.py` continua sendo usada pela composição de autenticação e pelo seeder.

## 3. Etapas executadas

| Fase | Resultado |
| --- | --- |
| 0 — Base, segurança e ferramentas | Branch criada a partir de `master`; estado local anterior preservado; 61 testes de integração passaram antes da extração. `pytest-cov`, `coverage.py` e Ruff foram declarados em `requirements-dev.txt`; `pyproject.toml` configura marcas, regras e estilo. |
| 1 — Catálogos | Controllers passaram a receber UUID e services coordenam CRUD, regras de nome e transação. SQLAlchemy foi isolado em repositories/adaptadores. |
| 2 — Despesas e entradas | Controllers só adaptam HTTP. Casos de uso validam períodos, referências, regras de reembolso e cronogramas; repositories mantêm consultas, agregações e gravações. |
| 3 — Contratos e transações | Commands/snapshots internos, erros de aplicação, `UnitOfWork` e contexto `atomic()` foram adicionados. Falhas de gravação fazem rollback no limite do caso de uso. |
| 4 — Autenticação e Google | Regras e resultados sem HTTP, repository SQL, adaptador Google, tokens e dependências de autenticação foram separados. Revogação de refresh comprometido continua confirmada antes da recusa. |
| 5 — Seeder e importador | Inicialização de referências e importação passaram a usar services, repositories e transação da aplicação; prévia, deduplicação e valores observados permaneceram. |
| 6 — Fechamento | Fixtures foram isoladas por marca de teste; unitários não carregam aplicação/`.env`; README, AGENTS e este plano foram atualizados. Sem migration por não haver mudança de esquema. |

## 4. Testes, ferramentas e cobertura

`pyproject.toml` define as marcas `unit` e `integration` e Ruff para Python 3.12. `tests/unit/` contém testes rápidos com colaboradores simulados; os testes restantes são classificados como integração e exercitam API, SQLAlchemy e SQLite em memória. A fixture SQLite habilita chaves estrangeiras e substitui `get_db`; não usa o PostgreSQL local.

As novas unidades cobrem regras de parcelas, limites de período, valores decimais, agregação de reembolsos, nomes de catálogos, transações, autorização OAuth e coordenação de despesas, entradas, catálogos, autenticação, seed e importador. Os controllers também são invocados diretamente com services simulados para verificar contratos de conversão e mapeamento de erros sem banco. Os testes existentes de API continuam cobrindo o fluxo HTTP e a persistência.

A cobertura foi medida somente com `tests/unit`, incluindo ramificações. No total de `backend/app`, o resultado foi 60% combinado (2.448 instruções e 404 ramificações). Esse denominador também inclui repositories SQLAlchemy, configuração, transporte externo e outros caminhos de infraestrutura, que têm cobertura complementar nas integrações. No recorte de regras e serviços de aplicação — `service.py`, `rules.py`, `shared/periods.py`, `shared/catalog_rules.py`, `shared/transactions.py` e `shared/reference_data_service.py` — a cobertura combinada foi 82% (564 instruções e 166 ramificações). A integração não foi somada à métrica unitária.

## 5. Comandos reproduzíveis

Execute a partir de `backend`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -m unit
.\.venv\Scripts\python.exe -m pytest -m integration
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\ruff.exe check app tests
```

Para verificar a formatação, use `ruff format --check` nos arquivos alterados da etapa; não reformate o restante do repositório por tabela. Para cobertura isolada, escolha um arquivo `--data-file` ainda inexistente, sem sobrescrever `.coverage` ou outro resultado local:

```powershell
.\.venv\Scripts\python.exe -m coverage run --data-file=.coverage.unit --branch --source=app -m pytest -m unit
.\.venv\Scripts\python.exe -m coverage report --data-file=.coverage.unit -m
```

## 6. Validação desta implementação

- Base antes da refatoração: `pytest` — 61 testes passaram.
- Resultado final: `pytest -m unit` — 48 passaram; `pytest -m integration` — 63 passaram; `pytest` — 111 passaram, com um aviso de depreciação da dependência Starlette/AnyIO.
- Ruff: `ruff check app tests` passou após ordenar imports e marcar imports intencionais da base existente; Ruff format `--check` passou nos 52 arquivos Python da implementação e dos testes.
- Cobertura unitária: comandos executados com arquivos de dados dedicados; `.coverage` preexistente foi preservado. Consulte os denominadores e percentuais na seção 4.
- Git: branch ativa `backend-refactor`, criada a partir da branch inicial `master`. A alteração preexistente em `lembrete-agents.md` foi preservada sem edição nesta tarefa.
- Não foram executados migrations, seeds, importações reais ou operações no PostgreSQL local. Como não houve mudança de esquema, não há migration a validar. SQLite em memória não comprova índices parciais nem diferenças de comportamento específicas do PostgreSQL.

## 7. Referências das ferramentas

- [Ruff — formatter](https://docs.astral.sh/ruff/formatter/)
- [Ruff — linter](https://docs.astral.sh/ruff/linter/)
- [coverage.py — ramificações](https://coverage.readthedocs.io/en/latest/branch.html)
