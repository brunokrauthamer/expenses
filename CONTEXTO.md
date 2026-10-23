# Contexto do projeto Expenses

Atualizado em 22/10/2026. Este documento resume decisões e o estado observado. Em novos chats, confira o código, o Git e as migrações antes de assumir que nada mudou.

## Objetivo e preferências

Aplicação web simples de controle de despesas pessoais. O usuário está desenvolvendo seu primeiro software com ajuda de um agente de programação e prefere explicações claras. Priorizar ferramentas gratuitas, evitar serviços pagos e não acrescentar funcionalidades sem solicitação. Não expor segredos nem executar comandos destrutivos sem autorização. O usuário solicitou execução dos testes disponíveis e correção de erros ao implementar mudanças.

A interface deve ser simples, responsiva e agradável, com aparência de aplicativo financeiro profissional: base clara, tons neutros, destaque para ações, tipografia legível, ícones consistentes e poucos elementos decorativos. A cor verde está proibida. Respeitar a preferência por movimento reduzido. Usar nomes em inglês para tabelas e colunas do banco.

Priorizar componentes e funções reutilizáveis, evitando renderizações e chamadas à API desnecessárias. Preservar as regras financeiras, integrações e dados reais; não apresentar controles sem função como se estivessem implementados. Manter português brasileiro, formatos locais de data e moeda, contraste, foco visível, navegação por teclado e experiência adequada ao celular.

## Organização

O projeto fica em `C:\Users\bruno\Documents\ChatGPT\expenses` e reúne frontend e backend no mesmo repositório:

```text
expenses/
  frontend/               React, Vite e CSS
    src/main.jsx          Navegação, layout e entrada do React
    src/pages/            Cadastro, histórico mensal e gastos consolidados
    src/components/       Painéis, estados, controles e gráficos SVG
    src/services/         Cliente HTTP compartilhado
    src/shared/           Cache, rotas, referências e formatação
    src/styles.css        Estilos e responsividade
  backend/                FastAPI, SQLAlchemy, Alembic e PostgreSQL
    app/config.py         Leitura de configuração
    app/database.py       Engine, sessão e base do SQLAlchemy
    app/main.py           Aplicação e registro das rotas
    app/modules/          Domínios auth, categories, expenses, income_entries e payment_methods
    app/shared/           Dependências e exceções compartilhadas
    migrations/           Migrações Alembic
    tests/                Testes da API
  .gitignore
```

O backend segue um monólito modular. Cada domínio tem arquivos `model.py`, `schema.py`, `service.py` e `controller.py`: modelos de banco, contratos da API, regras/consultas e rotas HTTP, respectivamente. A separação por domínio procura facilitar reaproveitamento futuro, sem assumir que já existam microsserviços.

## Estado funcional

O frontend possui navegação por History API entre `/despesas`, `/gastos` e `/consolidado`, com Header e Footer compartilhados e carregamento tardio das telas. O cadastro usa `POST /expenses`, consulta categorias e meios de pagamento no banco, permite compras à vista e parceladas e apresenta todos os pagamentos com vencimento no mês atual, uma linha por cobrança, ordenados pela data da compra. O valor exibido é o da parcela; compras parceladas indicam a parcela atual e o total de parcelas. O cabeçalho mostra a soma dos pagamentos do mês. Os registros persistem no banco após recarregar a página. Os filtros do consolidado e do histórico mensal ficam na URL.

A tela `/gastos` apresenta cobranças e reembolsos do mês selecionado em uma única lista, usando o mês atual como padrão. A lista combinada é paginada em lotes de até 100 itens e ordenada pela data do evento: vencimento para cobranças e recebimento para reembolsos. Cada reembolso aparece com valor negativo e texto vermelho, além da categoria de despesa vinculada. O resumo exibe gasto bruto, reembolsos recebidos e gasto líquido. Os filtros de categoria e busca se aplicam a ambos os tipos; o filtro por meio de pagamento afeta apenas cobranças, pois reembolsos não têm meio de recebimento. Despesas e reembolsos podem ser editados e excluídos pela mesma lista, usando seus formulários e rotas correspondentes. No celular, o `SectionSwitcher` alterna entre a lista e os filtros.

As telas ocupam a altura da janela, sem rolagem do documento. O arquivo `frontend/src/viewport.css` concentra as regras desse layout, importadas após os estilos visuais. Cabeçalhos e rodapé são compactos. As listas têm rolagem própria, mantendo título e total visíveis. Os campos do formulário podem rolar quando necessário, com o botão de salvar sempre disponível. Filtros, gráficos, tabelas abertas e avisos têm áreas de rolagem delimitadas. No celular (até 700 px), o componente reutilizável `SectionSwitcher` alterna entre formulário e pagamentos no cadastro, lista e filtros no histórico mensal e, no consolidado, entre evolução mensal, categorias e filtros. O rascunho do formulário é preservado ao alternar seções. A edição abre o formulário e foca a descrição, sem rolar a página inteira. O gráfico mensal adapta suas dimensões e a quantidade de rótulos à largura disponível.

Na lista de compras recentes há ações de edição e exclusão. A edição preenche o formulário, muda sutilmente a cor do painel para evidenciar o modo de edição e usa `PUT /expenses/{id}`; há opção de cancelar. A exclusão pede confirmação em um modal sobreposto, mostra a descrição e avisa quando todas as parcelas serão removidas. É possível cancelar pelo botão, pela tecla Escape ou pelo fundo; falhas aparecem no modal. O formulário exibe rótulos e validações junto aos campos, além de mensagens de sucesso ou erro.

O campo de valor recebe algarismos como centavos e posiciona a vírgula automaticamente: digitar `107643` resulta em `R$ 1.076,43`. A função reutilizável `formatAmountInput` fica em `frontend/src/shared/format.js`. O prefixo `R$` ocupa espaço próprio em um contêiner flexível para evitar sobreposição ao valor, inclusive no celular.

O consolidado usa `GET /expenses/summary` para apresentar total, evolução mensal e valores por categoria filtrados por período, categoria, meio de pagamento e busca. Os valores de compras parceladas entram pelo valor de cada parcela no mês de vencimento; representam cobranças, não pagamentos confirmados. O gráfico de evolução mensal é de barras, conforme a solicitação mais recente. Os gráficos SVG são responsivos, atualizados pelos filtros e oferecem valores por interação e tabelas acessíveis; as transições respeitam movimento reduzido. Os filtros ativos podem ser removidos individualmente ou limpos, e o período pode ser escolhido por atalhos ou intervalo personalizado.

O cliente HTTP usa `/api` por padrão, com opção de configurar `VITE_API_BASE_URL` no ambiente de compilação. No desenvolvimento e no preview, o Vite encaminha `/api` ao endereço de `BACKEND_PROXY_TARGET` (padrão `http://127.0.0.1:8000`) e remove o prefixo antes de enviar ao backend. As variáveis e exemplos estão em `frontend/.env.example` e `frontend/README.md`. Configurações `VITE_` são públicas no navegador e não devem conter credenciais. O proxy do Vite não serve como proxy de produção: a hospedagem deve encaminhar `/api` ao backend removendo o prefixo, ou definir uma URL pública de API na compilação; URLs de outra origem exigem CORS, que o backend ainda não configura. A hospedagem também deve encaminhar as rotas da interface para `index.html`. Ver chamadas a `localhost:5173/api/...` no navegador é esperado quando o proxy está ativo. Se a resposta for HTML da SPA em vez de JSON, conferir o endereço, o proxy e reiniciar o Vite; o cliente identifica esse caso e usa tempo limite de 15 segundos para evitar carregamento indefinido.

O cache compartilhado deduplica consultas, mantém referências por 30 minutos e resultados por 2 minutos e cancela leituras sem observadores. Cadastro, edição e exclusão de despesas invalidam as consultas de despesas, incluindo pagamentos do mês, histórico mensal e consolidado. Alterações em entradas invalidam as listas de entradas e o consolidado; na tela de histórico mensal também atualizam o resumo líquido e a lista de reembolsos. A busca do consolidado e do histórico mensal usa debounce; o período personalizado do consolidado é aplicado explicitamente para evitar requisições intermediárias desnecessárias.

Na revisão do layout, os cenários de API indisponível revelaram rejeições não tratadas nas chamadas deduplicadas do cache. O retorno dessas chamadas foi alinhado ao tratamento já existente da consulta original: falhas continuam no snapshot para exibição na interface, sem rejeitar uma promessa ignorada pelos assinantes. O cenário foi reproduzido e verificado no navegador.

O backend oferece GETs para categorias e meios de pagamento, uma lista de compras recentes sem duplicar parcelas, pagamentos por mês em `GET /expenses/month?month=AAAA-MM` (com valor e número da parcela) e um resumo agregado por mês/categoria. A listagem paginada aceita período inclusivo de até 120 meses, categoria e meio de pagamento em combinação com os filtros existentes. O seeder é um comando separado. Em instalações sem dados de referência, executá-lo conforme `backend/README.md` antes de usar o cadastro.

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

`20261018_0004` adicionou `expense_installments` e os campos do cronograma, convertendo cada gasto preexistente em uma cobrança única. A revisão mais recente está descrita na seção Entradas e reembolsos abaixo.

## Entradas e reembolsos

Implementado em 22/10/2026. O módulo `income_entries` usa `income_categories` e `income_entries`; o seeder cria Salário e Reembolso. A revisão Alembic `20261022_0006` foi aplicada ao PostgreSQL local partindo de `20261019_0005`, sem atualizar despesas existentes.

`GET /income-categories` lista as categorias. `GET/POST /income-entries`, `PUT /income-entries/{id}` e `DELETE /income-entries/{id}` implementam a lista paginada e CRUD. Reembolso exige `expense_category_id`; salário e outras categorias de entrada não a aceitam. O formulário permite criar, editar e excluir entradas, e mostra os recebimentos do mês.

`GET /expenses/history?month=YYYY-MM` devolve uma página única combinando cobranças e reembolsos do mês. A ordenação é global pela data do evento (vencimento da cobrança ou recebimento do reembolso), com `kind` distinguindo os tipos; o valor armazenado continua positivo e a interface exibe reembolsos negativos e em vermelho. Aceita `page`, `page_size` (máximo 100), `search`, `category_id` e `payment_method_id`; categoria e busca filtram ambos os tipos, enquanto meio de pagamento filtra apenas cobranças e mantém reembolsos na lista. Os totais `gross_expense_amount`, `reimbursement_amount` e `net_expense_amount` abrangem todos os itens filtrados, não apenas a página atual.

`GET /expenses/summary` devolve bruto, reembolso e líquido por mês e categoria. O bruto considera vencimentos de parcelas; o reembolso considera a data em que o dinheiro entrou. `total_amount_due` e `amount_due` mantêm compatibilidade como aliases do líquido. Se filtrar por meio de pagamento, o resumo não subtrai reembolsos, pois entradas ainda não têm meio de recebimento.

## Autenticação

Implementada em 22/10/2026. A migração Alembic `20261022_0007` cria `users`, `local_credentials`, `external_identities` e `refresh_sessions`. E-mail, nome e identificador Google são cifrados com AES-256-GCM; índices HMAC separados permitem localizar identidades sem manter os valores em claro; senhas usam Argon2id. JWT RS256 de acesso expira em 15 minutos. Refresh tokens opacos são rotacionados e enviados em cookie `HttpOnly`, `SameSite=Lax`; o frontend guarda o access token somente em memória e tenta renovar a sessão ao receber 401.

Todas as rotas de negócio exigem Bearer válido. Nesta primeira fase, as contas compartilham despesas, entradas, categorias e meios de pagamento. O frontend oferece `/entrar` e `/cadastro`. O fluxo Google usa Authorization Code com `state`, `nonce` e PKCE e só fica disponível depois de configurar as credenciais OAuth no backend. As chaves de criptografia e JWT precisam ser criadas e mantidas fora do Git; veja `backend/README.md`. A migração `20261022_0007` foi aplicada ao PostgreSQL local.

## Execução local

No primeiro uso, inicie o PostgreSQL, configure o backend e execute `python -m app.seed` a partir de `backend` para inserir as categorias e os meios de pagamento iniciais. Mantenha o FastAPI em execução enquanto usa a interface. Em seguida, a partir de `frontend`, com Node.js 20.19+ ou 22.12+ e pnpm:

```powershell
pnpm install
pnpm dev
```

Abrir o endereço informado pelo Vite, normalmente `http://localhost:5173`. O Vite encaminha `/api` ao FastAPI na porta 8000. Para gerar o build: `pnpm build`. Node e pnpm podem não estar no PATH do shell do agente. Em 19/10/2026, foi possível executar o build usando o Node do runtime integrado em `C:/Users/bruno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe` e o CLI local `frontend/node_modules/vite/bin/vite.js`, com diretório de trabalho em `frontend`.

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

Os testes usam SQLite em memória, não o PostgreSQL local. Em 22/10/2026, os 36 testes passaram após acrescentar cobertura para entradas, reembolsos e histórico combinado. O build do frontend também foi concluído. A migração `20261022_0006` foi aplicada ao PostgreSQL local; as tabelas e categorias iniciais foram criadas sem alterar despesas existentes.

## Git e GitHub

Frontend e backend ficam no mesmo repositório Git. O repositório GitHub `brunokrauthamer/expenses` foi criado pelo usuário e o remoto `origin` aponta para `https://github.com/brunokrauthamer/expenses.git`. O commit inicial `65e1b5c` (`Initial commit`) foi enviado para `master`.

A identidade usada no commit veio do perfil GitHub conectado: Bruno Krauthamer (`brunokrauthamer@gmail.com`). Ela foi configurada localmente neste repositório. Os ajustes de layout de 19/10/2026 estão na branch local `feat/viewport-layout`, criada a partir de `master`, sem commit ou push nesta etapa. Confirme a branch e o estado de trabalho antes de agir. O Git está disponível por `C:/Program Files/Git/cmd/git.exe`, mesmo quando ausente do PATH. Futuras melhorias devem usar branches separadas e PRs para `master`. Não há necessidade de branches principais `dev`, `qa` ou `staging`.

O primeiro push falhou sob a rede restrita do ambiente e foi concluído após autorização de rede. Se um push futuro falhar por conectividade, verificar a rede/autenticação GitHub e repetir com o acesso apropriado. A integração GitHub disponível no chat pode consultar recursos, mas não oferece criação de repositórios. Navegador e GitHub CLI não estavam disponíveis naquela sessão.

Antes de qualquer commit, revise os arquivos staged e assegure que segredos, ambiente virtual, dependências instaladas e arquivos gerados permanecem excluídos. O `.gitignore` cobre `.env`, ambientes virtuais, `node_modules`, builds, caches Python e cobertura.

