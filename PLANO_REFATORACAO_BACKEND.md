# Plano de refatoração do backend

Data da avaliação: 24/10/2026.

Status: planejamento; nenhuma mudança no código do backend foi feita nesta etapa.

Diretrizes gerais: [AGENTS.md](AGENTS.md).

Modelo de apresentação: [PLANO_REFATORACAO_FRONTEND.md](PLANO_REFATORACAO_FRONTEND.md).

Comportamentos e comandos atuais: [backend/README.md](backend/README.md).

## 1. Direção recomendada

Concluir a separação entre API, regras de negócio e persistência sem alterar os contratos HTTP nem as regras financeiras e de autenticação. A estrutura modular por domínio já escolhida para o Expenses deve ser mantida; o trabalho é tornar as responsabilidades internas de cada módulo claras.

SOLID, responsabilidades claras, migrations, seeds documentadas, testes unitários e recuperação são regras reutilizáveis. O monólito modular e os domínios `auth`, `categories`, `expenses`, `income_entries` e `payment_methods` são escolhas deste projeto. Outros projetos terão a arquitetura discutida na implementação.

O fluxo desejado é `controller → service → model/persistência`:

- `controller.py` recebe a requisição, usa os contratos de entrada, chama um caso de uso e transforma o resultado em resposta HTTP. Não manipula entidades ORM nem contém regras de negócio, consultas SQL ou transações.
- `service.py` implementa casos de uso e regras de negócio. Coordena a operação e a fronteira transacional por um contrato de persistência, sem depender de FastAPI, de detalhes HTTP ou de construir consultas SQLAlchemy.
- `model.py` representa os dados persistidos com SQLAlchemy. Consultas e gravações ficam na camada de modelo/persistência. Quando consultas complexas justificarem um arquivo próprio, um `repository.py` pode fazer parte dessa mesma camada; não é uma nova regra arquitetural para outros projetos.
- `schema.py` define contratos de entrada e saída da API. Tipos HTTP não devem ser usados como entidades de domínio ou persistência.

Dependências de infraestrutura, como a sessão SQLAlchemy, devem ser montadas fora dos handlers e entregues ao caso de uso pela composição do aplicativo. O controller não deve conhecer o modelo ORM de usuário; deve receber somente a identidade/contexto necessários à requisição.

Esta entrega atualiza o AGENTS e o planejamento. Instalação de ferramentas, movimentação de código, criação de testes e mudanças no banco pertencem às futuras etapas de implementação. A refatoração prevista não exige mudança de esquema, novas funcionalidades, troca de ORM ou reescrita da autenticação.

## 2. Diagnóstico do código atual

O backend já separa os domínios em módulos e os CRUDs mais simples delegam trabalho aos serviços. O problema está nos pontos em que os handlers também conhecem entidades e sessões do banco, transformam dados ou mantêm fluxos extensos de aplicação. Consultas SQL estão concentradas principalmente em `service.py` e `shared/catalog.py`; não se deve concluir que todos os controllers executam SQL diretamente.

Os arquivos dos domínios ficam em `backend/app/modules/`; `shared/` e os comandos CLI ficam em `backend/app/`. As observações se referem ao código local de 24/10/2026, não à arquitetura desejada.

| Área | Observação no código avaliado | Encaminhamento |
| --- | --- | --- |
| `expenses/controller.py` | Recebe `Session` e `User` ORM. Os endpoints de listagem percorrem entidades e relacionamentos ORM para montar respostas. `_validate_month_range` implementa validação de período e limite de 120 meses no controller. | Injetar um caso de uso; devolver DTOs/estruturas prontas para resposta; centralizar a validação de período e preservar os códigos e mensagens HTTP existentes. |
| `income_entries/controller.py` | Também recebe sessão e usuário ORM. Repete validação de intervalo mensal; os handlers de criação/edição coordenam serviço e `income_entry_payload`. | Reutilizar o validador de período e mover a composição do resultado para o service ou mapper apropriado, sem duplicar regra entre rotas. |
| `auth/controller.py` | Além de cookies e redirects, que pertencem à borda HTTP, conduz o fluxo Google: cria parâmetros de tentativa, troca código com o provedor, busca chave, valida claims, trata conflitos de banco, repete login e executa rollback. Importa `User` ORM e `IntegrityError`. | Deixar no controller apenas protocolo HTTP, cookies, redirects e mapeamento de falhas. Extrair autenticação com o provedor, validação de identidade e política de tentativa para um caso de uso/adaptador testável. |
| `categories/controller.py` e `payment_methods/controller.py` | Já delegam operações aos serviços e mapeiam erros de domínio para status HTTP. Ainda expõem sessão e entidade ORM do usuário nas assinaturas dos handlers. | Usar esses módulos como exemplos de extração pequena; remover dependência direta de ORM/SQLAlchemy do controller ao estabelecer a composição dos serviços. |
| `service.py` dos módulos | Regras e consultas SQLAlchemy estão juntas. Serviços filtram, agregam, leem/escrevem entidades e controlam commit/rollback, além de aplicar políticas de domínio. `expenses/service.py` concentra consultas de listagem, histórico, relatórios, parcelas e CRUD. | Separar consultas e persistência na fronteira de modelo/repositório; deixar no service a decisão de negócio e a coordenação transacional. Preservar consultas agregadas eficientes e escopo por usuário. |
| `auth/service.py` e `shared/auth.py` | O serviço lança `HTTPException` e define status/cabeçalhos. `shared/auth.py` mistura criação/validação de JWT, dependência HTTP e busca de usuário no banco. | Usar erros e resultados independentes de HTTP; separar a dependência Bearer das operações de token e da consulta de conta ativa. Preservar a resposta 401 e seu cabeçalho. |
| `shared/catalog.py` | Reúne normalização, SQL, escopo por conta, exclusão lógica, commit/rollback e uma condição específica de `IncomeCategory` que impede alterar a regra após uso. Categorias e meios de pagamento têm serviços que apenas delegam a esse helper. | Separar regra comum de nome, política específica de categoria de entrada e acesso a dados. Mover o helper inteiro para outro arquivo manteria o problema. |
| `expenses/schema.py` e entradas dos services | `ExpenseCreate.validate_payment_schedule` contém regras de parcelamento e limites financeiros; services de despesas e entradas recebem diretamente schemas da API. | Manter formato e tipos na borda. Tornar as regras de domínio utilizáveis pelo caso de uso sem criar um schema HTTP; adaptar comandos/resultados e preservar detalhes observáveis dos erros 422. |
| `seed.py`, `shared/reference_data.py` e `import_expenses.py` | A inicialização já participa da transação de criação da conta. Seeder e importador também acessam o ORM e definem commits; o importador tem prévia, deduplicação por conta e valores observados de parcelas. | Revisar os consumidores de persistência além das rotas. Preservar inicialização única e semântica da importação, usando arquivos sintéticos e banco descartável nos testes. |
| Testes | `backend/tests/` contém regressões via API e SQLite em memória e alguns testes diretos de funções de importação/criptografia. Chamar um serviço usando banco ainda é integração. `conftest.py` cria/remove tabelas somente no engine SQLite da fixture; essa suíte não executa Alembic. | Acrescentar testes unitários das regras e da coordenação com dependências substituídas; manter testes de API e persistência; medir cobertura unitária separadamente. A cobertura atual não foi medida. |
| Banco e dados iniciais | Alembic já versiona o esquema em `backend/migrations/versions/`. Os catálogos iniciais são criados por `shared/reference_data.py` no cadastro/login Google e pelo comando `app.seed`; o README documenta ambos. | Preservar o histórico de migrations e a semântica de inicialização única dos catálogos. Não reexecutar seeds sobre dados reais como parte da refatoração. |
| Ferramentas | `backend/requirements-dev.txt` inclui pytest, mas não declara Ruff ou ferramenta de cobertura; não há configuração de lint, formatação ou cobertura no backend. | Configurar ferramentas gratuitas e comandos na primeira fase de implementação. Sua adoção é proposta, não uma verificação já disponível ou executada. |

### O que preservar e pontos de atenção

- Os modelos já declaram constraints, índices e chaves compostas de propriedade. Preservar nomes e metadados para não gerar uma migration acidental ao mover código.
- O histórico combina cobranças e reembolsos antes de paginar. Totais completos e agregações não podem virar soma de uma página nem consultas por item.
- A duplicação de validação de período tem mensagens diferentes em despesas e entradas. Compartilhar a regra não autoriza uniformizar as respostas HTTP.
- `rotate_refresh` confirma revogação antes de recusar tokens reutilizados ou expirados. Um rollback automático de toda exceção apagaria um efeito de segurança esperado.
- O downgrade de `20261024_0008` recusa múltiplas contas e nomes incompatíveis com a unicidade global. Ele não é uma garantia de restauração completa dos dados anteriores.

## 3. Estrutura modular proposta

Manter os módulos existentes. A separação abaixo mostra responsabilidades conceituais; arquivos auxiliares só devem ser criados quando houver conteúdo real para eles.

```text
backend/app/modules/<dominio>/
  controller.py       # rotas, parâmetros HTTP, cookies/respostas e status
  schema.py           # contratos externos de entrada e saída
  service.py          # casos de uso, regras e coordenação transacional
  model.py            # entidades ORM e fronteira de persistência
  repository.py       # opcional: consultas/persistência complexas do Model
```

`repository.py` é opcional e pertence à camada Model; não deve virar um segundo lugar para regras de negócio. A montagem do FastAPI e suas dependências HTTP podem importar os módulos para compor a aplicação. Services e persistência não importam essa montagem nem dependências HTTP; helpers técnicos sem dependência da API podem ser compartilhados.

### Fronteiras e composição

| Área | Contrato esperado | Limite |
| --- | --- | --- |
| Controller e schema externo | Identidade autenticada, parâmetros validados no protocolo e resposta HTTP. | Sem sessão, entidades ORM, cliente Google, decisão financeira ou commit/rollback. Serialização final de um resultado simples continua na borda. |
| Service e regras puras | Comandos/resultados simples, erros de aplicação e operações de persistência necessárias ao caso de uso. | Sem `Request`, `Response`, `HTTPException` ou import de schemas externos. |
| Model/persistência | Consultas e gravações com escopo de conta, carregamento de dados, constraints e tradução de falhas técnicas conhecidas. | Sem status HTTP, política de negócio ou commit independente da transação do caso de uso. |
| Adaptador Google e operações criptográficas | Troca de código, obtenção de chave, validação de token e falhas próprias da integração. | Sem cookies, redirects ou regras de associação de contas no cliente de transporte. |
| Composição e dependências | Construção de serviços, adaptadores, sessão e mecanismo transacional; entrega da identidade à rota. | Sem regra de negócio escondida na injeção do FastAPI. |

Comandos/resultados podem ser estruturas simples ou dataclasses locais. Só criar `contracts.py`, `rules.py` ou um arquivo de consultas quando a responsabilidade extraída justificar o arquivo. Não exigir uma classe/interface para cada função nem um repositório genérico para todos os domínios.

O fluxo entre camadas é lógico. Para aplicar inversão de dependências, o service conhece o contrato das operações de dados; a composição entrega sua implementação SQLAlchemy. A abstração de transação pode ser pequena: contexto com commit/rollback e acesso aos colaboradores necessários. Escolher uma implementação coerente com a sessão atual, sem instalar um framework de injeção.

Dependências entre domínios ficam explícitas: despesas utiliza dados de reembolsos para consolidar resultados; autenticação coordena a inicialização dos catálogos da conta. Preservar contratos pequenos e sem ciclos; a persistência não importa services. A regra específica de reembolso hoje em `shared/catalog.py` pertence a `income_entries`, e código de composição entre módulos não deve se apresentar como helper genérico.

## 4. Plano de execução

Cada fase entrega uma parte utilizável, revisável e reversível. A cobertura unitária acompanha a extração de cada módulo desde o início; não fica concentrada na última fase.

| Fase | Entrega | Critério de aceite |
| --- | --- | --- |
| 0 — Base de comparação e ferramentas | Preservar o estado local; registrar contratos; executar suíte atual isolada; configurar lint, formatação e medição de cobertura. | Comandos reproduzíveis, resultados reais registrados e plano de retorno conhecido. Nenhuma conexão de teste usa o banco real. |
| 1 — Primeira separação completa | Aplicar controller → service → persistência a categorias e meios de pagamento; introduzir composição e transação pequenas. | Rotas sem ORM; regras testáveis sem banco; persistência com testes de integração; mesmos status, nomes, exclusão lógica e isolamento. |
| 2 — Consultas de despesas e entradas | Extrair regra de período, consultas, paginação, histórico, agregações e projeções de resposta. | Controllers recebem resultados simples; filtros, ordenação, contagem e totais preservados; nenhuma consulta por item introduzida. |
| 3 — Escritas financeiras e categorias de entrada | Separar regras de parcelamento/reembolso dos schemas HTTP e da persistência; compor cada gravação na transação do caso de uso. | Casos de uso funcionam sem schemas HTTP; sucesso, limites e falhas têm testes; falha no meio da escrita não deixa dados parciais. |
| 4 — Autenticação e Google | Separar erros de aplicação, dependência Bearer, operações de token, integração Google, associação de conta e criação/rotação de sessão. | Service sem FastAPI; controller sem cliente de provedor ou rollback; contratos de cookies, redirects e segurança preservados. |
| 5 — Seeds e importação | Adaptar CLI e inicialização de conta às fronteiras definidas e completar a documentação dos dados iniciais. | Mesma prévia, deduplicação e inicialização única; falhas restauram a transação; testes só usam planilhas e contas sintéticas. |
| 6 — Consolidação | Medir cobertura unitária final, revisar imports/metadados, remover caminhos antigos e atualizar README. | Critérios globais atendidos, suíte de API preservada e checks dos arquivos alterados passando. Migrations específicas de PostgreSQL verificadas quando afetadas. |

### Fase 0: comparação, segurança e legibilidade

- Verificar branch e alterações locais. Criar uma branch de implementação conforme as convenções do projeto, preservar arquivos não rastreados e dividir a entrega em commits pequenos. Não executar `reset --hard`, limpeza de arquivos ou recriação de banco para preparar o trabalho.
- Registrar contratos dos endpoints afetados: parâmetros, formatos decimais, aliases, ordenação/desempate, paginação, status, mensagens e estrutura dos erros de validação. A extração das validações de Pydantic precisa preservar os detalhes 422 ou tratar a incompatibilidade em uma alteração separada.
- Executar a suíte atual após confirmar o isolamento das fixtures. Identificar testes unitários existentes, distinguir os que usam API/banco e registrar a linha de base; um relatório de cobertura antigo não comprova o estado atual.
- Separar a configuração das fixtures de integração dos testes unitários. Evitar que importar uma regra ou serviço inicialize o engine real, carregue credenciais locais ou exija criar um cliente HTTP; configurações de teste são sintéticas e explícitas.
- Proposta de ferramentas gratuitas: Ruff para lint e formatação; coverage.py para linhas e ramificações. Adicionar dependências de desenvolvimento e configuração versionada compatíveis com o Python usado, documentando os comandos. Usar indentação de quatro espaços, imports organizados e regras de lint proporcionais ao projeto.
- Aplicar formatação nos arquivos tocados. Não reformatar todo o backend junto de uma extração funcional; se necessário, separar a adoção do estilo em mudança própria. Preservar imports deliberados de registro de modelos em `modules/registry.py`.

### Fases 1 a 3: separar sem mudar as regras financeiras

- Usar categorias e meios de pagamento para validar contratos de serviço/persistência, resultado simples e mecanismo transacional antes de replicá-los. A regra de nome ativo único permanece no service; a consulta e a proteção por constraint pertencem à persistência.
- Extrair validação de período para função pura reutilizada pelos casos de uso. Cobrir mês ou intervalo, par incompleto, mês inexistente, ordem invertida, 120 meses inclusivos e rejeição de 121. Mapear os erros na borda conforme o contrato de cada rota.
- Mover consultas e carregamento de relacionamentos para a persistência. Entregar projeções simples aos serviços e à serialização; não trocar navegação ORM no controller por lazy loading escondido em um DTO.
- Preservar `GET /expenses`, `/history`, `/recent`, `/month`, `/summary` e `/income-entries`. Compras e parcelas têm IDs e contagens diferentes; histórico pagina a união global; totais abrangem todo o filtro.
- Manter a diferença entre filtros de pagamento: no histórico filtram cobranças mantendo reembolsos; no resumo excluem reembolsos do cálculo. Manter bruto, reembolso, líquido e aliases atuais.
- Extrair cálculo de parcelas como função pura: entrada simples, saída com valores e datas; a persistência cria as entidades. Preservar resto na primeira parcela, limites monetários, data de compra, vencimento e comportamento em meses curtos/anos bissextos.
- Separar regras de referência ativa, retenção de referência antiga e vínculo de reembolso das consultas que fornecem os fatos. A política de `requires_expense_category` após uso permanece no módulo de entradas.
- Definir uma única transação por escrita. Criação da compra e parcelas, substituição do cronograma e exclusão com seus dependentes devem confirmar juntas; repositórios podem fazer flush, mas não commits independentes.

### Fase 4: autenticação com resultados explícitos

- Manter endpoints, leitura/escrita de cookies, status, cabeçalhos e redirects no controller. Trocar `HTTPException` no serviço por erros/resultados de aplicação, preservando o mapeamento HTTP, inclusive `WWW-Authenticate`.
- Extrair para um adaptador substituível a troca de código, busca de chaves e validação de assinatura/claims. O caso de uso coordena tentativa, identidade, vínculo e sessão. Testes não chamam Google nem baixam chaves reais.
- Preservar PKCE, `state`, `nonce`, expiração da tentativa, assinatura/audiência/emissor do token, e-mail verificado, política de domínio Google, destino interno permitido e identificador de tentativa.
- Manter a repetição controlada no conflito de identidade/sessão dentro da coordenação da aplicação, com rollback antes da repetição e sem cadastro parcial. Não acrescentar retries gerais.
- Separar criação e validação de JWT da dependência HTTP e da busca de usuário ativo. Entregar um contexto de identidade simples à rota, mantendo a autorização por conta nas consultas.
- Preservar os casos de revogação confirmada antes de erro no refresh. Diferenciar falha técnica, que exige rollback, de recusa de autenticação com efeito deliberado de segurança. Testar ambas.
- Preservar login local e Google, popup e redirecionamento, cookies HttpOnly, access token somente em memória e logs sem tokens, códigos OAuth ou segredos.

### Fases 5 e 6: consumidores auxiliares e fechamento

- Revisar `seed.py`, `shared/reference_data.py` e `import_expenses.py` para que a separação não se limite às rotas. Manter CLI como adaptação dos argumentos e apresentação de resultados; regras e persistência têm os mesmos limites dos casos de uso HTTP.
- Documentar no README a fonte versionada dos valores de seed, as 14 categorias de despesas, PIX/Cartão de Crédito e Salário/Reembolso com sua regra. Explicar escopo por conta, migrações prévias, execução automática/manual, transação e inicialização única.
- Preservar o marcador `reference_data_initialized_at`: repetição não repõe padrões renomeados ou excluídos; falha no cadastro desfaz também os catálogos. Não executar seed real para validar isso.
- Preservar a prévia e o `--apply` explícito do importador, exigência de `--user-id`, deduplicação por conta, cancelamento de importação parcial e cronogramas baseados nos valores observados. Não substituir essa regra pelo cálculo do formulário por conveniência.
- Remover helpers, imports e caminhos antigos só depois de migrar seus consumidores e testes. Revisar acoplamentos de `shared/` e o registro de modelos do Alembic.

### Recuperação e migrations em todas as fases

Refatorações sem mudança de esquema não criam migrations. Não aplicar migrations, seeds ou importações ao PostgreSQL real para verificar esta reorganização.

| Situação | Proteção e retorno exigidos |
| --- | --- |
| Código, configuração e documentos | Preservar o estado inicial e mudanças locais; usar commits pequenos ou cópias recuperáveis dos arquivos ainda não versionados. Reverter somente a etapa própria, sem descartar trabalho do usuário. |
| Escrita durante testes | Usar SQLite em memória ou PostgreSQL criado para a suíte; gerar fixtures sintéticas. Comprovar o destino do engine antes de criar/remover tabelas; a limpeza só atua no recurso descartável criado pelo teste. |
| Falha em operação composta | Injetar falha após a primeira escrita/flush e antes do commit; verificar rollback e ausência de registros parciais com uma nova leitura. Testar a preservação do cronograma anterior na edição. |
| Evolução de esquema, se necessária | Separar da extração, criar revisão Alembic nova e declarar efeitos nos dados. Testar upgrade vazio, atualização de legado sintético, falha transacional e downgrade seguro em PostgreSQL descartável compatível. |
| Qualquer operação persistente com risco de perda | Exigir backup completo dos dados e recursos afetados, comprovar restauração em ambiente isolado e registrar versões, sequência de restauração e como retomar escritas. Se não houver retorno comprovado, não executar. |

Não tratar downgrade como backup: reversões podem perder dados ou ser bloqueadas. A revisão `20261024_0008` já tem restrições explícitas; qualquer avaliação de reversão deve respeitá-las. Cópias reais, se indispensáveis a uma operação futura autorizada, são backups protegidos, nunca fixtures da suíte.

### Testes obrigatórios durante a implementação

| Tipo | Cenários prioritários |
| --- | --- |
| Unitários de regras | Nomes vazios/limites, duplicidade a partir dos fatos fornecidos, período, parcelas/centavos, datas extremas, reembolso, referência excluída e política de associação Google. |
| Unitários de coordenação | Service com persistência/provedor substituídos: proprietário, ausência, conflito, sucesso, falha após escrita, confirmação/rollback, rotação/reutilização de sessão e catálogo inicial na transação da conta. |
| Unitários da borda e adaptadores | Mapeamento dos erros, comandos/resultados, cookies e redirects; falha de rede, resposta incompleta e token inválido com transporte/chaves/relógio controlados. Invocar a unidade diretamente; testes HTTP continuam classificados como integração. |
| Integração de API e persistência | Preservar as suítes existentes de contratos, paginação, filtros, precisão financeira, constraints, escopo por usuário, exclusão lógica, histórico e rollback efetivo. |
| Integração específica de PostgreSQL | Quando afetados: índices parciais, chaves compostas, agregação mensal, bloqueio da rotação de refresh e migrations. SQLite não comprova esses comportamentos do PostgreSQL. |
| Seeds e importação | Inicialização repetida, falha sem criação parcial, item editado/excluído preservado, prévia sem gravação, aplicação atômica, duplicação total/parcial e mesma origem em contas distintas. |

Medir a suíte unitária isoladamente, cobrindo a maior parte das linhas executáveis de `backend/app` e acompanhando ramificações e lacunas por módulo. Preservar os testes existentes e acrescentar cenários críticos mesmo se o percentual agregado já for satisfatório. Não contar execução de imports como prova de comportamento nem somar a integração para declarar cobertura unitária; documentar o denominador e exclusões justificadas.

**Critério obrigatório em cada fase:** testes unitários pertinentes e checks dos arquivos alterados passam, contratos de integração afetados continuam passando e a etapa pode ser revertida isoladamente. Falhas preexistentes devem ser identificadas na base de comparação, sem serem atribuídas à extração nem ocultadas.

### Comandos disponíveis e propostos

Comando existente, executado a partir de `backend` com as dependências de desenvolvimento configuradas:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

As dependências são descritas em `requirements-dev.txt`; este plano não as instala. Ainda não há comando configurado para separar unitários, medir cobertura ou executar lint/formatação. Na fase 0, documentar os comandos efetivos após configurar as ferramentas e a seleção dos testes.

Exemplos propostos para depois dessa configuração; não foram executados nesta avaliação. Ajustar a lista ilustrativa aos arquivos de cada etapa:

```powershell
$arquivosDaEtapa = @('app/modules/categories/controller.py', 'app/modules/categories/service.py')
.\.venv\Scripts\python.exe -m ruff check $arquivosDaEtapa
.\.venv\Scripts\python.exe -m ruff format --check $arquivosDaEtapa
.\.venv\Scripts\python.exe -m coverage run --branch --source=app -m pytest tests/unit
.\.venv\Scripts\python.exe -m coverage report -m
```

`tests/unit` é uma organização proposta para os testes isolados; ela ainda não existe. Testes de integração atuais podem preservar seus nomes; se suas fixtures precisarem mudar de pasta para separar os ambientes, ajustar a coleta e os imports. A reorganização dos testes deve impedir que `conftest.py` imponha banco ou credenciais aos unitários. O formatter que grava arquivos deve receber somente os arquivos deliberadamente incluídos na etapa; `--check` apenas verifica.

## 5. Critérios de aceite

- Controllers não importam nem manipulam entidades ORM, `Session`, consultas ou operações de transação.
- Regras de negócio ficam em serviços e acesso ao banco na camada Model/persistência, com dependências na direção definida. Serviços não importam FastAPI nem schemas externos, não constroem SQL e não dependem de objetos HTTP; dependências entre módulos são explícitas e sem ciclos.
- Endpoints, schemas, status HTTP, regras de autorização e resultados financeiros permanecem compatíveis com os testes de contrato existentes.
- Testes unitários cobrem a maior parte do código executável em medição separada da integração e os cenários críticos de sucesso, erro, limites e rollback; testes de API continuam cobrindo as fronteiras públicas.
- O conjunto de testes e as verificações de migration não usam nem alteram dados reais. Para qualquer operação persistente há uma restauração recuperável já verificada.
- Migrations existentes permanecem imutáveis; migrations novas, se necessárias, são revisáveis e têm comportamento de reversão documentado.
- Seeds têm dados, pré-requisitos, escopo, comando, transação e repetição documentados; catálogos editados ou excluídos não são repostos pela refatoração.
- Formatação e lint têm comandos reproduzíveis, e o diff não contém reformatação não relacionada.

## 6. Validação desta avaliação

Esta etapa alterou apenas `AGENTS.md` e este plano. A análise foi feita pela leitura dos READMEs, contexto local, plano do frontend, controllers, services, schemas, modelos, infraestrutura compartilhada, seed/importador, fixtures, testes e estrutura de migrations, incluindo as restrições da revisão `20261024_0008`. O Git foi consultado: a branch era `master`, com os dois documentos já presentes como arquivos não rastreados. Seus conteúdos anteriores foram copiados para backup temporário e os hashes foram conferidos antes da edição.

Foram revisados os diffs em relação às cópias iniciais, as referências locais e a coerência dos comandos com os arquivos do projeto. A verificação documental também conferiu UTF-8, fechamento dos blocos de código e ausência de marcadores de conflito.

Não foram executados testes, lint, formatter Python, build, migrations, seeds, importações ou alterações no banco: o escopo foi exclusivamente documental. A cobertura atual não foi medida. Os comandos e verificações das fases descrevem trabalho futuro.

## 7. Referências técnicas para as ferramentas propostas

- [Ruff — formatter](https://docs.astral.sh/ruff/formatter/): formatação automática e verificação com `--check`.
- [Ruff — linter](https://docs.astral.sh/ruff/linter/): seleção gradual de regras e verificação dos arquivos da etapa.
- [coverage.py — ramificações](https://coverage.readthedocs.io/en/latest/branch.html): medição das alternativas de execução além das linhas.
