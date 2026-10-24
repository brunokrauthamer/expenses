# Plano: dados por usuário e cadastros personalizáveis

Data: 24/10/2026.

Status: implementação de código concluída na branch `feat/user-owned-finances`, criada a partir do commit `40d5b4d`. Modelos, migração Alembic, isolamento do backend, CRUD dos catálogos, inicialização por usuário, importador, tela `/configuracoes` e cache protegido por conta foram implementados. Passaram **53 testes do backend**, o teste focado de resposta atrasada do cache e o build de produção do frontend. A migration foi ensaiada em PostgreSQL 17 descartável com instalação vazia, dados legados (incluindo parcelas, reembolso e fonte de importação) e recusa de propriedade ambígua com rollback. A revisão visual desktop/celular permanece pendente: a automação do navegador encerrou porque não conseguiu determinar a URL atual do Chrome com confiança. A migration não foi aplicada ao banco real, nenhum dado financeiro real foi alterado e ainda não houve push ou PR.

## Resultado esperado

Cada usuário terá suas próprias despesas, entradas, categorias de despesas, categorias de entradas e meios de pagamento. Somente o proprietário poderá consultar, criar vínculos, editar ou excluir seus registros. As despesas e entradas existentes, assim como seus cadastros de referência, serão atribuídas ao único usuário atualmente cadastrado, preservando IDs, valores, datas, parcelas e relacionamentos.

Categorias e meios de pagamento poderão ser adicionados, renomeados e excluídos pelo proprietário. A exclusão será lógica: o item sai das opções de novos lançamentos, mas continua disponível para identificar, buscar, filtrar e agregar lançamentos antigos em qualquer consulta histórica atual ou futura.

## Situação encontrada no código

- FastAPI, SQLAlchemy e Alembic no backend; React e cache próprio no frontend.
- `users.id` já usa UUID; a revisão Alembic atual é `20261022_0007`.
- `app/main.py` exige autenticação nas rotas de negócio, mas os serviços não recebem o usuário e consultam dados compartilhados.
- `expenses` e `income_entries` não têm proprietário. As parcelas e fontes de importação pertencem à despesa.
- `categories`, `income_categories` e `payment_methods` são globais, com nome único e somente listagem pela API. Existem schemas de criação para categorias de despesas e meios, ainda sem rotas correspondentes.
- `IncomeCategory.requires_expense_category` determina se uma entrada é reembolso. Histórico e consolidado dependem dessa propriedade, não apenas do nome da categoria.
- `useExpenseLookups.js` entrega as mesmas referências aos formulários e às consultas; as telas resolvem nomes pelos IDs nessas listas.
- `queryCache.js` mantém dados em memória com chaves sem usuário; `AuthContext.jsx` ainda não limpa esse cache na saída ou troca de conta.
- O seeder e o importador de planilhas usam cadastros globais e também precisarão receber o proprietário.

## Regras de funcionamento

### Propriedade e acesso

1. O backend obtém `user_id` exclusivamente de `get_current_user`. Não aceitar proprietário escolhido no corpo, nos filtros ou na URL das rotas comuns.
2. Toda operação de serviço recebe explicitamente o `user_id` autenticado. Helpers de consulta reutilizáveis sempre exigem esse argumento, sem modo global como padrão.
3. Aplicar o escopo antes da paginação, contagem e agregação. Incluir despesas recentes, parcelas do mês, entradas, as duas partes da união do histórico, totais de reembolso e consolidado.
4. Buscar registros a editar/excluir pelo par proprietário e ID. Retornar 404 para ID inexistente ou pertencente a outra conta, sem revelar sua existência.
5. Categorias e meios vinculados também devem pertencer ao mesmo usuário. IDs de outra conta são rejeitados com 404; referências próprias excluídas são rejeitadas com 422 quando usadas em um novo vínculo.
6. Parcelas e fontes de importação herdam o proprietário pela despesa. Nenhuma consulta isolada dessas tabelas pode contornar o vínculo com `expenses.user_id`.
7. Novos usuários começam sem lançamentos financeiros e recebem cópias próprias dos cadastros iniciais. Cadastro local e primeiro login Google usam a mesma inicialização; vincular uma identidade Google a uma conta existente não cria outro catálogo.

### Exclusão e histórico

1. Usar `deleted_at`, nulo enquanto o item está ativo, nos três cadastros de referência. Mesmo itens ainda não utilizados serão excluídos logicamente, simplificando a regra e mantendo IDs estáveis.
2. Nunca excluir em cascata despesas, entradas, reembolsos ou parcelas ao excluir uma referência. Preservar as restrições de integridade.
3. Novos lançamentos e trocas de referência só aceitam itens ativos. Isso também vale para a categoria do gasto reembolsado.
4. Ao editar um lançamento antigo, permitir manter exatamente a referência excluída que ele já possui. Exibi-la como “excluída”, apenas naquele campo e registro; não oferecê-la para outros lançamentos. Se houver mudança de referência, exigir uma ativa.
5. Excluir uma referência não modifica lançamentos nem parcelas futuras já programadas. Seus valores continuam compondo os meses e os totais correspondentes.
6. Histórico e relatórios consultam referências ativas e excluídas. Não adicionar `deleted_at IS NULL` aos joins financeiros nem aplicar filtro global de exclusão no ORM que esconda essas relações.
7. Nomes permanecem disponíveis em listas, resultados de busca, filtros, rótulos e gráficos. A implementação deve centralizar a resolução histórica para futuras telas herdarem essa regra.
8. Renomear atualiza o nome apresentado também no histórico, mantendo o ID e os valores. Não faz parte desta entrega guardar versões anteriores do nome.
9. Permitir reutilizar um nome excluído criando um novo ID. O histórico permanece vinculado ao ID antigo; filtros distinguem o item excluído. Não reativar nem transferir vínculos antigos silenciosamente.

### Nomes e categorias de entrada

- Remover espaços nas extremidades, rejeitar nomes vazios e respeitar o limite atual de 50 caracteres. Comparar nomes ativos sem diferenciar maiúsculas/minúsculas dentro do mesmo usuário e do mesmo cadastro; duplicidade retorna 409. Tratar também a concorrência pelo índice único.
- Contas diferentes podem usar os mesmos nomes. Categorias de despesas, categorias de entradas e meios de pagamento continuam em tabelas separadas.
- A interface permite definir se uma categoria de entrada representa reembolso, com explicação de que ela exigirá categoria do gasto e reduzirá o gasto líquido.
- `requires_expense_category` não pode mudar depois de a categoria ter qualquer entrada vinculada, pois isso reclassificaria o histórico. A API retorna 422 nesse caso; antes do primeiro uso, a alteração é permitida. Renomear ou excluir não muda essa propriedade.
- Salário e Reembolso serão apenas padrões iniciais individuais: ambos podem ser renomeados ou excluídos. A regra de reembolso nunca depende do texto do nome.
- Não adicionar meio de recebimento às entradas nesta entrega; elas atualmente não possuem esse campo.

## Modelo de dados proposto

| Tabela | Alterações |
| --- | --- |
| `expenses` | `user_id` UUID obrigatório, FK para `users.id`, com índice. |
| `income_entries` | `user_id` UUID obrigatório, FK para `users.id`, com índice. |
| `categories` | `user_id` obrigatório e `deleted_at` com fuso; substituir unicidade global de nome por unicidade de nome ativo por proprietário. |
| `income_categories` | Mesmas alterações, preservando `requires_expense_category`. |
| `payment_methods` | Mesmas alterações, preservando o tipo INTEGER do ID. |
| `users` | `reference_data_initialized_at` opcional para controlar inicialização individual sem recriar padrões renomeados/excluídos. |
| `expense_import_sources` | Acrescentar `user_id` e trocar unicidade global de `source_key` por `(user_id, source_key)`; garantir que o proprietário seja o da despesa. |
| `expense_installments` | Sem proprietário duplicado; manter vínculo obrigatório à despesa. |

Adicionar chaves únicas `(id, user_id)` nas referências e em `expenses`, com FKs compostas nos vínculos para impedir relações entre contas também no banco:

- `expenses(category_id, user_id)` → `categories(id, user_id)`.
- `expenses(payment_method_id, user_id)` → `payment_methods(id, user_id)`.
- `income_entries(income_category_id, user_id)` → `income_categories(id, user_id)`.
- `income_entries(expense_category_id, user_id)` → `categories(id, user_id)`, mantendo a categoria de despesa opcional.
- `expense_import_sources(expense_id, user_id)` → `expenses(id, user_id)`.

Usar `ON DELETE RESTRICT` nas referências ao usuário e nos cadastros financeiros; não criar exclusão de conta nesta entrega. Alinhar explicitamente os relacionamentos SQLAlchemy às FKs compostas para evitar joins ambíguos ou escrita conflitante de `user_id`.

Criar índices únicos parciais por `(user_id, lower(trim(name))) WHERE deleted_at IS NULL` nos três cadastros. Antes de criá-los, verificar conflitos nos dados antigos; interromper com diagnóstico em vez de mesclar IDs automaticamente. Manter compatibilidade de modelos/testes com SQLite e validar a migração no PostgreSQL.

Prever índices de consulta em `expenses(user_id, expense_date)` e `income_entries(user_id, received_date)`; verificar os índices de `expense_installments(expense_id, due_date)` conforme as consultas existentes. Medir necessidade de outros índices com dados representativos, sem criar todos os cruzamentos de filtros.

## Migração dos dados existentes

Criar revisão Alembic posterior a `20261022_0007`, sem editar migrações já aplicadas.

1. Fazer backup e registrar contagens, totais financeiros, quantidades de parcelas e vínculos de importação antes da atualização. Executar a entrega com a aplicação parada, evitando escritas concorrentes entre migração e atualização do código.
2. Consultar a tabela `users` na própria migração. Se houver registros legados, exigir exatamente um usuário e usar seu UUID, sem embutir e-mail ou ID no código. Se houver zero ou vários usuários com dados legados, abortar antes de atribuir qualquer registro; será necessário definir explicitamente o proprietário antes de repetir. Em instalação vazia, permitir migrar sem usuário e criar os padrões no primeiro cadastro.
3. Acrescentar `user_id` inicialmente anulável e `deleted_at` aos cadastros; adicionar o controle de inicialização em `users`.
4. Atribuir despesas, entradas, três cadastros e fontes de importação ao único usuário. Preservar todos os IDs existentes e não recriar parcelas.
5. Validar que não restam proprietários nulos, referências órfãs, vínculos entre contas ou conflitos de nomes ativos. Conferir contagens e totais, inclusive bruto, reembolso e líquido por mês/categoria.
6. Criar FKs, unicidades e índices; remover a unicidade global dos nomes e de `source_key`; tornar os proprietários obrigatórios.
7. Completar somente os padrões ausentes do catálogo legado, se necessário, e marcar `reference_data_initialized_at`. A inicialização futura não deverá repor itens que o usuário renomeou ou excluiu.
8. Confirmar a revisão e testar o acesso da conta original. Criar uma segunda conta de teste para verificar a separação sem alterar os lançamentos reais.

Executar o processo em transação no PostgreSQL. Testar falha e rollback por pré-condições inválidas. Não tratar downgrade com múltiplas contas como operação segura: a estrutura antiga mistura proprietários e não comporta nomes iguais entre contas. Documentar restauração pelo backup como recuperação; eventual downgrade deve bloquear perda de isolamento ou conflitos, sem apagar ou mesclar dados automaticamente.

## Backend e contratos da API

### Rotas financeiras

Preservar URLs e regras financeiras atuais, passando o usuário autenticado dos controllers aos serviços:

- Despesas: `GET/POST /expenses`, `PUT/DELETE /expenses/{id}`, `GET /expenses/recent`, `/month`, `/history` e `/summary`.
- Entradas: `GET/POST /income-entries` e `PUT/DELETE /income-entries/{id}`.
- Helpers envolvidos: `_filtered_expenses`, `_get_expense`, `_validate_references`, `_entry_filters`, `_validate_entry` e `reimbursement_totals`.

Adicionar validações distintas para criação e edição, levando em conta as referências anteriores do registro. Rejeitar envio de `user_id` nos schemas de escrita. As respostas históricas devem incluir nome e estado das referências necessárias à exibição, além dos IDs existentes, para não dependerem de uma lista de opções ativas. Usar schemas/helpers comuns para essa representação.

### Cadastros individuais

Aplicar o mesmo contrato a `/categories`, `/income-categories` e `/payment-methods`:

| Operação | Contrato |
| --- | --- |
| `GET /...` | Somente itens ativos do usuário, em ordem alfabética. |
| `GET /...?include_deleted=true` | Ativos e excluídos do usuário, para gestão e filtros históricos. |
| `POST /...` | Criar item individual; HTTP 201. |
| `PUT /.../{id}` | Renomear item ativo; categoria de entrada também pode alterar sua regra somente antes do primeiro uso. |
| `DELETE /.../{id}` | Preencher `deleted_at`; HTTP 204. Repetir para item próprio já excluído retorna 204. |

Respostas incluem `id`, `name` e `deleted_at`; categorias de entradas incluem `requires_expense_category`. Escrever em item excluído retorna 422, exceto repetir a exclusão. Não incluir restauração nesta entrega.

### Inicialização e importação

- Extrair helper transacional de criação dos padrões por usuário e chamá-lo em `_new_user`, compartilhado pelo cadastro local e Google. Não efetuar commit independente do cadastro; rollback deve remover também o catálogo criado.
- Adaptar `python -m app.seed` para exigir `--user-id`, validar o proprietário e respeitar `reference_data_initialized_at`. Repetições não recriam itens, inclusive após renomear/excluir todos os padrões. Não executar seed de todos os usuários implicitamente no login ou na inicialização do servidor.
- Adaptar o importador para exigir `--user-id` tanto na prévia quanto na gravação e filtrar referências e fontes por esse proprietário. Validar referências ativas e falhar com diagnóstico quando o mapeamento de nomes não for possível.
- A repetição da mesma planilha continua sem duplicação para a mesma conta; o mesmo arquivo pode ser importado por outra conta sem consultar ou bloquear fontes da primeira.

## Frontend

1. Criar tela `/configuracoes`, acessível pela navegação, com seções para categorias de despesas, categorias de entradas e meios de pagamento. Reutilizar componentes de lista, formulário e confirmação de exclusão.
2. Oferecer adicionar, renomear e excluir; explicar na confirmação que lançamentos anteriores serão preservados. Mostrar os itens excluídos em uma seção própria identificada, sem ações de reutilização nessa entrega.
3. Separar opções de cadastro (ativas) e referências de consulta (incluindo excluídas) em hooks reutilizáveis. Em chaves de cache, incluir proprietário e modo da consulta; nunca deduplicar uma lista ativa com uma histórica.
4. Usar os dados de referência devolvidos pelos registros para rótulos históricos; incluir excluídos nos filtros do mês e consolidado, com identificação textual. Ao editar, preservar a opção excluída já vinculada conforme a regra do backend.
5. Manter ícone genérico para nomes personalizados sem mapeamento em `CategoryIcon`; não exigir novo ícone para cada nome.
6. Incluir `user.id` em todas as chaves de consultas de negócio. Na saída, expiração e troca de conta, cancelar requisições, invalidar sua geração e limpar snapshots, timers e dados anteriores antes de exibir a próxima sessão. Uma resposta atrasada da conta anterior não pode repovoar o cache nem o estado atual, mesmo se ignorar cancelamento.
7. Ao criar, editar ou excluir uma referência, invalidar as listas ativa/histórica e consultas financeiras afetadas do usuário, pois nomes são usados em buscas e rótulos. Atualizar selects e filtros sem recarregar a página inteira.
8. Se todos os itens ativos forem excluídos, mostrar estado vazio com acesso à configuração para adicionar novos. Remover instruções antigas que pedem executar seeder para corrigir ausência de categorias/meios na interface.
9. Revisar destinos internos permitidos do login local e Google para admitir `/configuracoes`; preservar os controles de segurança atuais do retorno OAuth.
10. Preservar responsividade, teclado, foco, mensagens em português, movimento reduzido, ausência de verde e layout de altura da janela.

## Sequência de implementação

1. **Persistência — concluída:** atualizados os modelos, criada a migration `20261024_0008`, implementadas FKs compostas e inicialização dos catálogos. Ensaiada em PostgreSQL 17 descartável com banco vazio, dados sintéticos legados e propriedade ambígua; não foi usada cópia dos dados reais.
2. **Isolamento — concluído:** `user_id` propagado pelas rotas e serviços financeiros, consultas, contagens, totais, importador e fixtures. Os testes cobrem acesso entre duas contas e vínculos inválidos.
3. **Cadastros — concluída:** CRUD individual dos três catálogos, exclusão lógica, unicidade por conta e regra de categoria de reembolso implementados.
4. **Histórico — concluído:** schemas, consultas, filtros e edição preservam referências excluídas e seus rótulos nos registros antigos.
5. **Interface e sessão — implementação concluída; revisão visual pendente:** criada `/configuracoes`, cache separado por conta e limpeza na troca de sessão. O teste focado confirma que uma resposta antiga não repovoa o cache limpo. Falta revisar os fluxos visuais em desktop e celular.
6. **Validação e entrega — parcialmente concluída:** 53 testes do backend, teste Node do cache, build de produção e ensaio da migration passaram; documentação atualizada. A automação do navegador encerrou por não conseguir identificar com confiança a URL atual do Chrome. Não houve push nem PR; a revisão visual ainda é um critério de aceite deste plano.

## Aprendizados da execução

- `Base.metadata.create_all` em SQLite valida os modelos e as FKs, mas não substitui um ensaio da migration em PostgreSQL. O ensaio descartável confirmou o SQL e o comportamento transacional da migration sem acessar o banco real.
- O ensaio legado cobriu uma despesa com duas parcelas, um reembolso e uma fonte de importação. Contagens, IDs e valores permaneceram iguais após a atribuição do proprietário. Com dois usuários e dados de catálogo sem proprietário, a migration recusou a atualização e o PostgreSQL reverteu a transação, mantendo o schema na revisão anterior.
- O primeiro ensaio da migration detectou que o PostgreSQL inferia tipos diferentes (`text` e `varchar`) para o parâmetro de nome na consulta de inserção dos catálogos padrão. A comparação foi corrigida com `CAST`, e os cenários foram executados novamente com sucesso.
- Uma resposta HTTP pode ignorar o cancelamento; limpar apenas o cache não basta. A geração da consulta precisa mudar antes de limpar os snapshots para impedir que a resposta tardia publique dados da conta anterior. O teste focado cobre esse caso.
- A revisão visual requer acesso confiável à página aberta. A ferramenta de automação parou ao não conseguir determinar com confiança a URL da janela atual do Chrome; por isso, os fluxos visuais e a alternância real de contas continuam pendentes.
- O PostgreSQL descartável foi desligado e removido. A migration não foi aplicada ao PostgreSQL local e nenhum dado financeiro real foi alterado.

## Validação e critérios de aceite

### Testes automatizados

- Ajustar `tests/conftest.py`: o usuário autenticado precisa ser persistido e estável, com duas contas e catálogos distintos. A fixture atual devolve um UUID novo e usuário não persistido em cada chamada.
- Testar contas A e B com despesas, parcelas e entradas próprias no mesmo mês. Nenhuma lista, busca, paginação, contagem, soma, histórico combinado ou consolidado de A contém dados de B, e vice-versa.
- Testar tentativa direta de editar/excluir IDs alheios e usar referências alheias em despesas, entradas e reembolsos: 404 e nenhuma alteração. Testar que o corpo não define `user_id`.
- Testar FKs compostas com inserções diretas inválidas, garantindo que a proteção não dependa apenas da API.
- Testar exclusão de cada tipo de referência: desaparece de novos cadastros, criação direta com ela falha, referências históricas e buscas continuam disponíveis e os totais são idênticos antes/depois. Cobrir parcelas futuras já existentes.
- Testar edição de lançamento com referência excluída: pode manter a anterior ou trocar por ativa; não pode adotar outra excluída. Cobrir também reembolso e a categoria do gasto reembolsado.
- Testar nomes iguais em contas distintas, conflito na mesma conta, espaços/caixa, reuso do nome excluído e diferenciação dos IDs no histórico.
- Testar que renomear/excluir Reembolso não muda sua natureza financeira e que alterar `requires_expense_category` depois do uso é rejeitado.
- Testar padrões por conta no cadastro local e primeiro login Google, vínculo de conta existente sem duplicação, rollback do cadastro e repetição de seed após renomeações/exclusões.
- Testar importação repetida na mesma conta e arquivo igual em contas distintas.
- Testar a migração em PostgreSQL descartável/cópia: estado legado com um usuário, instalação vazia e recusa de propriedade ambígua. Comparar contagens, IDs, valores, parcelas, reembolsos, fontes e totais; SQLite com `create_all` não verifica a migração real.
- Cobrir o cache com resposta atrasada: sair de A, entrar em B e só então concluir a consulta antiga de A. Os dados de A não podem aparecer. Usar testes focados com as ferramentas de teste do frontend disponíveis, adicionando suporte mínimo se necessário.
- Executar a suíte completa do backend, incluindo autenticação/importação/relatórios, e `pnpm build` no frontend.

### Verificação de interface

- Cadastrar, renomear e excluir cada tipo de referência em desktop e celular.
- Excluir uma referência já usada e verificar mês, consolidado, busca, filtro e edição de registros antigos, incluindo reembolsos.
- Excluir todas as opções de um cadastro e confirmar que há caminho para adicionar uma nova, sem formulário inutilizável ou seleção inválida.
- Alternar entre duas contas na mesma aba e testar logout, expiração e retorno pelo Google, verificando ausência de dados anteriores.

## Limites desta etapa

Este plano inclui categorias de entradas na personalização, além das categorias de despesas. Não inclui compartilhamento entre usuários, administradores globais, transferência de lançamentos entre contas, restauração de referências, auditoria de nomes anteriores ou meios de recebimento. A migração no banco real depende de backup e janela de manutenção; publique a mudança apenas depois de validar a cópia PostgreSQL e completar o build e a revisão visual descritos nos critérios de aceite.
