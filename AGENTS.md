# Diretrizes para agentes de desenvolvimento

Este arquivo orienta a construção e a manutenção do projeto. A base abaixo pode ser copiada para novos repositórios; substitua a seção **Contexto deste repositório** e adapte as convenções à stack escolhida. Não copie regras específicas de negócio para projetos sem relação com este domínio.

As regras gerais de backend, SOLID, versionamento do banco, testes e reversibilidade valem para qualquer projeto. A organização por módulos do Expenses é uma decisão local, documentada somente no contexto deste repositório. Em outro projeto, discuta e registre a arquitetura durante a implementação; não imponha a mesma árvore de pastas.

## Base reutilizável

### 1. Entender antes de alterar

- Leia as instruções aplicáveis, o README, os scripts e o código envolvido. Verifique branch e alterações locais antes de editar; preserve trabalho existente.
- Use o código atual e verificações reais como evidência. Planos e documentos podem descrever um estado antigo ou ainda não implementado.
- Identifique o comportamento esperado, os consumidores afetados e os critérios de aceite. Pergunte quando uma decisão ausente mudar materialmente o resultado; resolva detalhes rotineiros com as convenções existentes.
- Entregue o escopo solicitado. Uma tarefa de planejamento produz diagnóstico e plano; a implementação começa quando fizer parte do pedido.

### 2. Responsabilidades e organização

- Organize por responsabilidade e proximidade. Um arquivo deve ter um motivo claro para mudar; extraia blocos quando misturarem interface, regras, transporte e efeitos difíceis de acompanhar.
- Páginas compõem a tela e coordenam seu fluxo. Formulários, listas e filtros com responsabilidades próprias devem ser componentes identificáveis.
- Componentes exclusivos ficam próximos de sua página ou componente proprietário. Promova para a área compartilhada quando houver consumidores independentes reais.
- Primitivas visuais com uso transversal confirmado podem nascer compartilhadas. Não crie abstrações para usos apenas imaginados.
- Uma página não importa outra página para reutilizar componentes, hooks ou helpers. Extraia o que ambas precisam.
- Preserve fronteiras de dependência e evite ciclos. A camada de transporte não importa páginas, componentes ou stores da aplicação.
- Tamanho de arquivo é um sinal para revisão, não uma regra automática de linhas. Dividir um arquivo sem melhorar responsabilidades não encerra a refatoração.

### 3. Princípios e camadas de backend

- Siga os princípios SOLID em qualquer projeto. Aplique-os para manter responsabilidades e dependências claras, sem criar abstrações para cenários que ainda não existem.
- Defina as camadas e seus contratos antes de ampliar uma arquitetura. A escolha concreta de arquitetura pertence a cada projeto e deve ser registrada no contexto daquele repositório.

#### Aplicação de SOLID

| Princípio | Diretriz prática |
| --- | --- |
| Responsabilidade única (S) | Cada unidade tem um motivo claro para mudar. Protocolo externo, regra de negócio e persistência têm responsáveis distintos. |
| Aberto/fechado (O) | Permita extensões nos pontos de variação comprovados por requisitos; evite condicionais espalhadas e generalizações especulativas. |
| Substituição de Liskov (L) | Implementações alternativas preservam contratos, invariantes, resultados e erros esperados pelos consumidores. |
| Segregação de interfaces (I) | Ofereça contratos pequenos e específicos; consumidores não devem depender de operações que não usam. |
| Inversão de dependências (D) | Regras de negócio dependem de contratos claros para persistência e integrações, com implementações montadas na composição da aplicação e substituíveis em testes. |

#### Contratos entre camadas

- `controller` expõe a API e adapta o protocolo externo: recebe e valida a forma da requisição, chama um caso de uso, converte resultados em respostas HTTP e mapeia erros para status apropriados. Não implementa regras de negócio, consultas SQL, persistência, controle de transação ou manipulação direta de entidades ORM.
- `service` executa casos de uso, aplica regras de negócio e coordena operações. Não depende de objetos HTTP nem decide status ou cabeçalhos de resposta. Delega consultas e gravações aos contratos da camada de persistência; não concentra SQL ou chamadas diretas de consulta e gravação da sessão ORM.
- `model` representa o domínio persistido e integra os dados com o banco: mapeamentos ORM e operações de consulta e persistência ficam nessa fronteira. Se o volume ou a complexidade justificar repositórios explícitos, eles pertencem à camada de persistência/modelo; não acrescente uma camada sem uma responsabilidade real.
- Mantenha dependências em uma direção clara: controller → service → model/persistência. Tipos de transporte não devem vazar para regras de negócio ou persistência, e a camada de dados não deve importar camadas superiores.
- Validação de formato, presença e limites do protocolo pode ficar no contrato de entrada. Regras que dependem do domínio pertencem ao service. Não duplique a mesma regra em controllers diferentes.
- Contratos de entrada e saída da API são distintos dos dados de entrada e resultado dos casos de uso. Adapte-os na borda; não entregue entidades ORM ao controller para que ele navegue por relacionamentos ou dispare consultas ao serializar.
- A composição da aplicação monta serviços, persistência e integrações. Controllers recebem o caso de uso e a identidade necessária à requisição, sem assumir o ciclo de vida de conexões ou transações.
- Essas fronteiras também valem para helpers chamados pelo controller. Mover a lógica para uma função auxiliar no mesmo arquivo ou repassá-la a um helper que mistura camadas não resolve a separação.
- Faça cada operação que grava dados dentro de uma transação coerente, coordenada pelo caso de uso por um contrato de persistência. Defina commit e rollback em um único limite; operações auxiliares não confirmam gravações parciais. Falhas técnicas devem restaurar o estado anterior. Quando a regra exigir uma gravação seguida de recusa, como revogar uma sessão comprometida, explicite e teste esse resultado para que a revogação não seja desfeita pelo tratamento do erro.

#### Banco de dados, migrations e seeds

- Versione toda mudança no esquema do banco por migrations da ferramenta adotada pelo projeto, incluindo tabelas, colunas, índices e constraints. Transformações de dados necessárias à evolução do esquema também fazem parte da migration. Não dependa de alterações manuais ou sincronização automática do ORM em bancos persistentes; criação direta de tabelas fica restrita a fixtures descartáveis.
- Não reescreva migrations já aplicadas. Crie uma nova revisão, preserve a ordem e inclua downgrade quando for tecnicamente seguro. Documente limitações quando uma reversão exata não for possível.
- Migrations devem declarar claramente o efeito sobre dados existentes. Avalie cenários de banco vazio e já populado; valide comportamento específico do banco usado pelo projeto em um ambiente descartável compatível.
- Documente seeds iniciais: quais dados criam (ou sua fonte versionada), para qual ambiente/escopo, pré-requisitos, quando e como executá-las, se são repetíveis, quem confirma a transação e o que acontece com dados já editados. Seeds não devem restaurar silenciosamente dados que usuários removeram ou alteraram. Separe dados iniciais da aplicação de fixtures sintéticas de testes e de exemplos de demonstração.
- Nunca use dados financeiros ou outros dados reais como fixture. Toda verificação que grava dados deve usar banco descartável, cópia isolada ou transação cuja restauração tenha sido comprovada.

#### Reversibilidade, testes e legibilidade

- Mudanças de código, dados, configuração e testes devem ser não destrutivos e ter um caminho de retorno conhecido antes de começar. Divida o trabalho em etapas reversíveis. Preserve o estado anterior em controle de versão, transações ou backup recuperável e confira como restaurá-lo antes de operações com dados. Arquivos locais não rastreados e trabalho ainda não commitado também precisam ser preservados; o Git sozinho não garante sua recuperação.
- Testes não podem apagar, sobrescrever ou migrar bancos reais, arquivos do usuário ou ambientes compartilhados. Use fixtures isoladas e dados sintéticos; testes de migrations devem operar em banco descartável.
- Testes unitários devem cobrir a maior parte do código executável, com prioridade para regras, validações, cálculos, transformações, limites e erros. Testes de integração complementam essa cobertura para contratos entre camadas, API e banco.
- Meça a cobertura da suíte unitária separadamente da integração e acompanhe linhas e ramificações relevantes. Um teste que usa API ou banco, mesmo em memória, verifica integração; ele não comprova cobertura unitária. Não aumente índices com testes sem comportamento útil nem exclua regras difíceis de testar apenas para atingir uma meta.
- Mantenha testes rápidos, determinísticos e sem credenciais ou serviços externos reais. Controle relógio, rede e respostas externas. Inclua regressão para defeitos corrigidos e verifique que falhas de gravação fazem rollback.
- Use o formatador e o linter configurados para a stack; aplique indentação consistente e convenções reconhecidas pela linguagem. Prefira uma ferramenta automática de formatação a alinhamentos manuais. Se não houver configuração, inclua ferramentas gratuitas adequadas e comandos reproduzíveis na etapa de implementação pertinente. Evite reformatar arquivos não relacionados ao escopo.
- Consulte os comandos realmente configurados no projeto antes de executar ou documentar verificações. Não reporte como executado algo que foi apenas planejado.

### 4. Convenção para frontends com componentes

Use esta base quando compatível com a stack e com as decisões do projeto:

```text
src/
  main.jsx                  # inicialização
  App.jsx                   # composição da aplicação
  index.css                 # tokens e base global
  components/
    Button/
      index.jsx
      index.css
  pages/
    ExamplePage/
      index.jsx
      index.css
      useExamplePage.js
      LocalComponent/
        index.jsx
        index.css
  assets/
  services/
  shared/
  store/
```

- `components`: apresentação reutilizável e componentes de negócio compartilhados.
- `pages`: páginas, seus componentes exclusivos e lógica local.
- `assets`: imagens, vídeos, fontes, animações e outros arquivos estáticos.
- `services`: comunicação com APIs e fontes externas, sem JSX ou hooks de UI.
- `shared`: funções e constantes reutilizáveis sem React, estado global ou efeitos de navegador.
- `store`: estado compartilhado, sessão, cache, assinaturas e coordenação de suas atualizações.
- Hooks exclusivos ficam próximos de seus consumidores; hooks que assinam o cache ou a sessão ficam junto dessa infraestrutura. Um hook não pertence automaticamente a `shared`.
- Use nomes de componentes/páginas em PascalCase e nomes descritivos para hooks e funções. O prefixo `use` é reservado a hooks.
- Cada componente ou página tem `index.jsx`; estilos próprios ficam em `index.css`, quando existirem. Não crie CSS vazio ou pastas sem função.
- Mantenha testes unitários próximos do código testado, com nomes `*.test.js` ou `*.test.jsx` conforme o conteúdo. Suítes que exercitam a integração entre módulos podem ficar em uma pasta de testes própria.
- Prefira imports explícitos. Evite um arquivo central que reexporte todos os componentes e conecte áreas independentes.
- Adapte as extensões à linguagem escolhida no projeto. Não introduza migração de linguagem como efeito colateral de uma extração.

### 5. Componentes e contratos

- Use HTML semântico dentro dos componentes. Extraia padrões de aparência, acessibilidade ou comportamento; elementos simples de composição podem continuar no JSX da página.
- Antes de criar Button, Input, Select, diálogo ou mensagem, procure a implementação existente e evolua-a quando adequado.
- Primitivas visuais recebem dados e callbacks; não conhecem endpoints, regras de autenticação ou chaves de cache.
- Preserve atributos nativos, acessibilidade, referência ao elemento e uso por teclado. Defina claramente a responsabilidade por rótulos, ajuda e erros.
- Prefira composição e poucas variantes a dezenas de booleanos ou um componente genérico que decide todos os fluxos da aplicação.
- Button usa `type="button"` por padrão; submissão é explícita. Ações com ícone precisam de nome acessível. Estado pendente impede acionamento duplicado e é comunicado.
- Select usa o elemento nativo enquanto o produto não exigir comportamento adicional. Opções e regras de negócio são preparadas fora do controle genérico.
- Diferencie mensagens de erro, sucesso, carregamento e atualização. Falha de requisição não representa lista vazia ou valor zero.

### 6. Estado e fluxo de dados

- Mantenha campos, validação, diálogos e estado de envio no menor proprietário adequado.
- Para estado compartilhado entre poucos componentes, considere primeiro seu ancestral comum e props. Use estado global para necessidades compartilhadas concretas.
- Dados remotos têm uma fonte de verdade no cache; não os copie para contextos e estados locais sem necessidade explícita.
- Quando filtros e paginação pertencem à URL, derive o estado aplicado dela. Rascunhos temporários ficam locais e possuem regra clara de aplicação.
- Hooks reutilizam lógica; não compartilham automaticamente suas instâncias de estado.
- Separe validação e transformação puras de efeitos de rede. Cálculos derivados não exigem outro estado sincronizado por efeito.
- Não adicione `memo`, `useMemo` ou `useCallback` indiscriminadamente. Use-os para exigências de identidade ou desempenho observadas.

### 7. Comunicação externa e sessão

- Centralize transporte HTTP, timeout, cancelamento e tratamento de erros. Serviços por domínio reutilizam esse cliente.
- Mantenha a direção das dependências: UI/coordenação → operações e cache → serviços → transporte. Helpers reutilizáveis não importam camadas superiores.
- Requisições obsoletas não podem sobrescrever resultados atuais. Respostas de uma sessão anterior não podem repovoar dados da sessão seguinte.
- Defina chaves, validade e invalidação de consultas. Não acrescente polling, retries ou consultas redundantes sem necessidade.
- Separe efeitos de cache do transporte: o serviço faz a operação externa; a coordenação atualiza ou invalida as consultas afetadas.
- Preserve o modelo de autenticação existente. Não exponha tokens, segredos ou credenciais em URLs, logs, documentação ou código entregue ao navegador.

### 8. CSS, acessibilidade e experiência

- Mantenha tokens visuais em uma fonte global: cores, tipografia, espaçamentos, bordas, raios e transições.
- Estilos próprios ficam junto de seus componentes e páginas. Um CSS local importado continua global se não houver um mecanismo real de isolamento; delimite seus seletores.
- Não dependa da ordem de visita das rotas para a interface funcionar. Evite redefinições globais e remendos de especificidade a cada tela nova.
- Preserve foco visível, rótulos associados, contraste, teclado, alvos de toque e movimento reduzido.
- Diálogos precisam de nome e descrição, foco inicial adequado, cancelamento definido e retorno de foco.
- Verifique desktop, celular, conteúdo longo, carga, vazio e erro quando afetados pela mudança. Controles visíveis precisam ter comportamento real.

### 9. Qualidade e verificação

- Consulte os scripts disponíveis antes de indicar comandos. Não invente validações nem relate como executado o que está apenas planejado.
- Rode os checks existentes pertinentes à mudança. Ao mover arquivos, atualize imports, lazy imports, estilos, testes e referências afetadas.
- Testes unitários são obrigatórios para regras de negócio, validações, transformações, cálculos e comportamentos relevantes de hooks e componentes criados ou alterados. Em refatorações, preserve os testes existentes e acrescente cobertura para comportamentos relevantes ainda desprotegidos nos módulos afetados.
- Correções de defeitos devem incluir um teste unitário de regressão que reproduza o problema e verifique o resultado esperado.
- Testes unitários devem ser isolados, rápidos e determinísticos, sem depender de API, banco de dados ou credenciais reais. Controle relógio, timers e respostas externas quando necessário; preserve a lógica sob teste.
- Configure o ambiente e um comando de execução dos testes unitários desde o início do projeto. Cada etapa de implementação só está concluída quando os testes unitários pertinentes passam; build, revisão visual e testes de integração complementam essa verificação.
- Evite testes triviais de wrappers e testes que apenas repetem a implementação. Priorize cenários de sucesso, erro e limites dos contratos, sem exigir um teste para cada elemento de marcação.
- Verifique componentes pelo comportamento observável: rótulos, ações, estado pendente, retorno de erro e recuperação.
- Complemente os testes unitários com testes de integração para os contratos afetados entre camadas, API e persistência, e com testes de ponta a ponta (end-to-end) para os fluxos de usuário afetados. Testes de API e de DOM isolado não substituem a execução do fluxo completo pela interface; informe separadamente o que cada suíte verificou.
- Configure lint e formatação de maneira proporcional à stack. Não misture reformatação geral, atualização de dependências e mudança funcional em uma refatoração pequena.
- Em mudança exclusivamente documental, revise conteúdo, referências, comandos e diff; build não é obrigatório se nenhum código ou configuração de execução mudou.
- Se uma verificação não puder ser executada, informe exatamente qual ficou pendente e por quê.

### 10. Mudanças e comunicação

- Prefira entregas pequenas e utilizáveis. Diferencie movimentação de arquivos, mudança de arquitetura, correção funcional e alteração visual.
- Não preserve defeitos confirmados como requisito. Registre sua reprodução e trate a correção de maneira identificável, com verificação adequada.
- Use a stack e o gerenciador de pacotes existentes. Justifique dependências novas e mantenha o lockfile coerente; não atualize versões incidentalmente.
- Atualize a documentação relevante quando contratos, comandos ou decisões mudarem. Não reescreva histórico como se uma proposta já estivesse implementada.
- Documente o código quando contratos, regras de negócio, limites ou decisões não forem evidentes. Use docstrings e comentários para explicar o motivo e as invariantes relevantes; mantenha-os atualizados junto da implementação e evite comentários que apenas repitam o código.
- Preserve arquivos do usuário e dados reais. Não execute operações destrutivas ou publique alterações fora do escopo autorizado.
- Antes de qualquer ação destrutiva, especialmente em banco de dados, tenha backup completo dos dados e recursos afetados, confira se ele pode ser recuperado e defina como restaurá-lo. Sem backup recuperável e procedimento de restauração conhecido, não execute a ação, mesmo que ela faça parte do escopo autorizado.
- Não leia nem imprima segredos sem necessidade para a tarefa; nunca os inclua em artefatos ou commits.
- Ao concluir, informe o que mudou, como foi verificado e quais limitações materiais restam, em linguagem clara.

## Contexto deste repositório

Esta seção é específica do **Expenses**. Substitua-a ao usar este arquivo como base em outro projeto.

### Stack e fontes locais

- Monorepositório: `frontend` com React, Vite, JavaScript/JSX e CSS; `backend` com FastAPI, SQLAlchemy, Alembic e PostgreSQL.
- Gerenciador do frontend: pnpm. Preserve `frontend/pnpm-lock.yaml`.
- Leia [sistemaDePastas.md](sistemaDePastas.md), [CONTEXTO.md](CONTEXTO.md), [frontend/README.md](frontend/README.md) e [backend/README.md](backend/README.md) conforme a tarefa.
- [lembrete-agents.md](lembrete-agents.md) reforça backup e restauração antes de ações destrutivas, testes unitários, documentação de código e testes de integração e ponta a ponta.
- Os planos de arquitetura do frontend e do backend estão em [PLANO_REFATORACAO_FRONTEND.md](PLANO_REFATORACAO_FRONTEND.md) e [PLANO_REFATORACAO_BACKEND.md](PLANO_REFATORACAO_BACKEND.md). São propostas, não descrevem mudanças já implementadas; a presença deles não autoriza uma reorganização completa fora da tarefa solicitada.
- O projeto é uma aplicação de controle de despesas pessoais. O usuário está desenvolvendo seu primeiro software: prefira explicações claras em português brasileiro, ferramentas gratuitas, evite serviços pagos e não acrescente funcionalidades sem solicitação.
- Use nomes em inglês para tabelas e colunas do banco.
- O [CONTEXTO.md](CONTEXTO.md) contém histórico de branches, verificações e migrations. Confirme o estado atual no Git e nos arquivos; não trate contagens antigas de testes, versões de runtime ou migrations anteriormente aplicadas como evidência atual. A estrutura do frontend já evoluiu em relação à árvore registrada nesse documento; confira [frontend/README.md](frontend/README.md) e o código.

### Backend deste projeto

- O backend usa Python, FastAPI, SQLAlchemy, Alembic e PostgreSQL. Migrations ficam em `backend/migrations/versions/`.
- A arquitetura escolhida para o Expenses é um monólito modular organizado por domínio em `backend/app/modules/`, com os módulos `auth`, `categories`, `expenses`, `income_entries` e `payment_methods`. Esse arranjo é específico deste projeto; a arquitetura de outros projetos deve ser discutida na implementação.
- Os módulos atuais possuem `controller.py`, `schema.py`, `service.py` e `model.py`; infraestrutura compartilhada fica em `backend/app/shared/`. A separação ainda precisa ser concluída conforme [PLANO_REFATORACAO_BACKEND.md](PLANO_REFATORACAO_BACKEND.md).
- Pendências confirmadas no código: controllers de despesas e entradas validam regras de período; o controller de autenticação coordena integração Google, conflitos de banco e rollback; services e `shared/catalog.py` misturam regras com consultas e gravações. Essa situação deve ser corrigida nas etapas de refatoração, sem ser adotada como padrão para código novo.
- O processo e os dados iniciais do Expenses estão documentados em [backend/README.md](backend/README.md): a conta recebe catálogos no cadastro ou primeiro login Google; `python -m app.seed --user-id <UUID-DA-CONTA>` inicializa manualmente os catálogos de uma conta e registra a inicialização uma única vez.
- O importador `python -m app.import_expenses --user-id <UUID-DA-CONTA>` oferece uma prévia sem gravação; `--apply` grava os itens. Preserve a exigência do proprietário e a deduplicação das mesmas fontes dentro da conta, sem executar importações reais em verificações.
- A migration `20261024_0008` atribui dados legados a uma única conta e exige exatamente um usuário quando há esses dados; preserva registros e IDs e verifica conflitos de nomes, vínculos, contagens e totais. O downgrade bloqueia bancos com mais de um usuário. Sua execução em banco real exige backup recuperável e janela sem escritas; confirme a revisão aplicada sem presumir que o histórico do contexto ainda esteja atualizado.
- O backend usa testes com SQLite em memória; essa configuração não substitui verificações específicas de PostgreSQL para migrations ou comportamento dependente do banco.
- As dependências de desenvolvimento atuais incluem pytest, mas não configuram formatador, linter ou ferramenta de cobertura. Sua adoção está prevista no plano do backend; não relate esses checks como disponíveis antes de configurá-los.

### Comportamentos a preservar

- Interface em pt-BR, moeda BRL e datas de calendário sem deslocamento de dia. Não usar verde no tema.
- Preserve a aparência financeira profissional: base clara, tons neutros, ações destacadas, tipografia legível, ícones consistentes e poucos elementos decorativos.
- Rotas de negócio: `/despesas`, `/gastos`, `/consolidado` e `/configuracoes`; autenticação em `/entrar`, `/cadastro` e conclusão Google em `/auth/complete`.
- Login local e Google coexistem. Preserve validações de origem, janela e identificador no popup, fallback por redirecionamento e restrição do destino de retorno a rotas internas permitidas.
- Preserve o Google Authorization Code com PKCE, `state`, `nonce` e validação do ID token no backend. O popup comunica apenas o resultado, sem tokens. O vínculo automático a uma conta local pelo e-mail só é permitido para Gmail ou domínio Workspace confirmado pelo Google.
- Access token JWT RS256 com validade padrão de 15 minutos somente em memória; refresh token rotativo em cookie `HttpOnly`, `SameSite=Lax`. Preserve a renovação ao receber 401 e a restauração da sessão após recarregar. Não mover tokens para localStorage ou sessionStorage.
- E-mail, nome e identificador Google são cifrados com AES-256-GCM, com índices HMAC separados para busca; senhas usam Argon2id. Mantenha as chaves fora do Git e preserve a leitura dos dados cifrados durante rotações conforme o procedimento do backend.
- Todas as rotas de negócio exigem Bearer válido. Consultas, contagens, paginação, relatórios e alterações usam o proprietário autenticado; IDs de outra conta retornam 404. Preserve as chaves estrangeiras compostas que impedem vínculos entre contas.
- O cache de dados privados é separado por conta e limpo/cancelado no logout ou na troca de sessão. Referências ativas e históricas têm chaves distintas.
- Referências têm validade atual de 30 minutos; resultados, 2 minutos; retenção inativa, 5 minutos. Não alterar essas políticas incidentalmente.
- Preserve deduplicação de consultas, cancelamento de leituras sem observadores e exposição de falhas no snapshot do cache, sem rejeições de promessas ignoradas por assinantes. Alterações em despesas invalidam pagamentos do mês, histórico e consolidado; alterações em entradas atualizam suas listas, reembolsos, resumo líquido e consolidado.
- Categorias de despesas, categorias de entradas e meios de pagamento têm CRUD por conta em `/configuracoes`, nomes ativos únicos sem diferenciar maiúsculas de minúsculas e exclusão lógica. Reutilizar um nome excluído cria outro ID. Referências excluídas continuam identificáveis em históricos, buscas, filtros, totais e edições antigas; novos lançamentos usam opções ativas. Consultas históricas usam `include_deleted=true`; edições podem manter a referência excluída que já possuíam.
- Categorias de entrada definem o vínculo com despesas por `requires_expense_category`, independentemente do nome. Quando verdadeiro, `expense_category_id` é obrigatório; quando falso, é rejeitado. Essa regra não pode mudar depois do primeiro lançamento vinculado. Salários e outros ganhos não reduzem despesas.
- Compra, parcela e entrada são entidades diferentes. Cobranças contam pelo vencimento; reembolsos, pelo recebimento. São cobranças programadas, não pagamentos confirmados. No histórico combinado, busca e categoria filtram ambos os tipos; meio de pagamento filtra apenas cobranças e mantém reembolsos. No consolidado, o filtro por meio de pagamento exclui reembolsos do cálculo.
- `/gastos` usa o mês atual por padrão, combina cobranças e reembolsos em uma lista paginada e ordena globalmente pela data do evento. Reembolsos têm valor positivo na API e no banco, mas aparecem negativos e em vermelho na interface, com a categoria de despesa vinculada. Preserve os totais bruto, de reembolsos e líquido, e os aliases `amount_due` e `total_amount_due` do líquido no resumo.
- `GET /expenses` lista cobranças: `id` identifica a compra, `installment_id` identifica a cobrança, `amount_due` é o valor da parcela e `total_amount` é o total da compra. `total` conta cobranças, não valores monetários. `month=AAAA-MM` filtra pela cobrança; sem período, retorna todas as programadas. A busca considera descrição, categoria e meio de pagamento sem diferenciar maiúsculas de minúsculas. A paginação usa `page=1` e `page_size=20` por padrão, com máximo de 100 itens; períodos inclusivos aceitam até 120 meses. Confira os parâmetros próprios de cada endpoint.
- Compras aceitam `payment_type=one_time|installments` e `amount_type=total|installment`; `installment_count` vai de 1 a 1200 e parcelados exigem ao menos 2 parcelas. `first_installment_date` assume `expense_date` quando ausente. PUT altera a compra inteira e recalcula o cronograma quando mudam valor, datas ou quantidade; DELETE remove a compra e todas as cobranças, com resposta 204.
- Totais completos vêm da API quando disponíveis. Subtotal de uma página de resultados deve ser identificado como tal.
- Valores financeiros exatos usam strings decimais ou centavos inteiros; não introduza soma monetária por ponto flutuante. Conversão para escala de gráfico não deve virar fonte de totais.
- Datas, máscaras, regras de parcelamento e associação de reembolsos não podem mudar como efeito de uma extração de componentes.
- A máscara monetária recebe algarismos como centavos: `107643` resulta em `R$ 1.076,43`. Preserve `formatAmountInput` em `frontend/src/shared/format.js` e o espaço próprio do prefixo `R$`, inclusive no celular.
- Preserve a navegação por History API, Header e Footer compartilhados e carregamento tardio das telas. No cadastro, a lista do mês mostra uma linha por cobrança, ordenada pela data da compra, com valor da parcela, indicação da parcela atual e quantidade total quando parcelada, e soma mensal no cabeçalho.
- Preserve os filtros do histórico e do consolidado e a paginação do histórico na URL, debounce de busca, aplicação explícita do período personalizado e remoção individual ou limpeza dos filtros ativos.
- As telas financeiras ocupam a altura da janela com rolagem interna delimitada, títulos e totais visíveis e botão de salvar disponível. No celular (até 700 px), `SectionSwitcher` alterna as seções preservando o rascunho; a edição abre o formulário e foca a descrição sem rolar o documento inteiro. As regras atuais ficam junto dos componentes e páginas, não no antigo `viewport.css` citado no contexto.
- A edição permite cancelar e evidencia seu estado no painel. A exclusão pede confirmação, identifica o registro, avisa sobre a remoção de todas as parcelas e mantém falhas visíveis no diálogo; botão, Escape e fundo permitem cancelar.
- O gráfico de evolução mensal é de barras. Preserve gráficos SVG responsivos, rótulos adaptados à largura, valores por interação, tabelas acessíveis e respeito a movimento reduzido.
- Não aplique migrações ou altere dados financeiros reais como parte de tarefas de frontend ou documentação.

### Ambiente, transporte e Git

- A API usa `/api` por padrão; `VITE_API_BASE_URL` altera a base na compilação. Variáveis `VITE_` são públicas e nunca recebem credenciais. No desenvolvimento e preview, o Vite encaminha `/api` a `BACKEND_PROXY_TARGET` (padrão `http://127.0.0.1:8000`) removendo o prefixo. Reinicie o Vite após mudar o ambiente.
- O proxy do Vite não atende produção: a hospedagem deve encaminhar `/api` ao backend removendo o prefixo ou usar uma URL pública de API definida no build. Outra origem exige CORS, ainda não configurado no backend. As rotas da interface precisam retornar `index.html`. Preserve o timeout HTTP de 15 segundos e o diagnóstico de HTML recebido em lugar de JSON; confira endereço e proxy nesse cenário.
- O PostgreSQL é local, inspecionado pelo pgAdmin; `DATABASE_URL` fica em `backend/.env`, com modelo em `backend/.env.example`. Reutilize `backend/.venv` e recrie o ambiente apenas quando necessário. Em produção, use HTTPS, `AUTH_COOKIE_SECURE=true` e caminho de cookie compatível com o prefixo público da API (padrão `/api/auth`).
- `iniciar.ps1` inicia os servidores e abre `http://localhost:5173`. Preserve o Uvicorn com `--no-access-log` para não registrar `code` e `state` do callback OAuth.
- Melhorias devem usar branches separadas e PRs para `master`; não é necessário criar branches principais `dev`, `qa` ou `staging`. Confirme branch e alterações locais antes de agir e preserve logs e arquivos não rastreados.
- Antes de commits, revise os arquivos staged e confirme que segredos, chaves, ambientes virtuais, dependências, builds e caches permanecem excluídos. Preserve as regras do `.gitignore`, incluindo `.env` e `client_secret_*.json`.
- Se Git não estiver no PATH, verifique `C:/Program Files/Git/cmd/git.exe`. Em falhas de push por conectividade, confira rede e autenticação e use o acesso autorizado, sem presumir que limitações de ferramentas relatadas em sessões antigas ainda existam.

### Comandos disponíveis

Dentro de `frontend`:

```powershell
pnpm dev
pnpm build
pnpm test
pnpm test:unit
pnpm test:dom
pnpm lint
pnpm format:check
pnpm format
node --test tests/queryCache.test.js
```

O `package.json` atual configura `test` (Node e Vitest), `test:unit` (Node), `test:dom` (Vitest, jsdom e Testing Library), `lint` (ESLint) e formatação (Prettier). O comando direto do cache continua útil para a verificação focada. `pnpm format` escreve nos arquivos; evite formatação geral fora do escopo.

Confira os requisitos de Node em `frontend/README.md` e nas dependências atuais; a versão citada no contexto é histórica. Se Node/pnpm não estiverem no PATH do shell, verifique os runtimes já disponíveis antes de propor instalação. O contexto registra como alternativa o Node em `C:/Users/bruno/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe`, usando `frontend/node_modules/vite/bin/vite.js` para o build a partir de `frontend`; confirme disponibilidade e compatibilidade antes de usar.

Dentro de `backend`, com o ambiente virtual e dependências de desenvolvimento configurados:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Consulte os READMEs antes de configurar ambientes. Testes do backend usam SQLite em memória; isso não substitui a verificação específica de uma migração PostgreSQL quando ela fizer parte da tarefa.
