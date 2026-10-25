# Plano de refatoração do frontend

Data da avaliação: 24/10/2026.
Status: planejamento; nenhuma mudança no código da aplicação foi feita nesta etapa.
Referência de organização: [sistemaDePastas.md](sistemaDePastas.md).
Diretrizes para trabalhos futuros: [AGENTS.md](AGENTS.md).

## 1. Direção recomendada

Transformar as páginas em pontos de composição: elas escolhem quais blocos aparecem, conectam os dados necessários e coordenam a navegação. Formulários, listas, filtros, estados de consulta e regras de transformação passam a ter donos claros.

O problema não é usar HTML no JSX: `section`, `form`, `label`, `button` e `select` continuam sendo a base correta da interface. O ganho vem de encapsular padrões que repetem aparência, acessibilidade ou comportamento. Não precisamos criar um componente para cada `div`.

Adotar a estrutura solicitada, com componentes e páginas em pastas com `index.jsx` e estilos próximos em `index.css`. Corrigir apenas a grafia de `assests` para `assets`. Componentes exclusivos ficam dentro da pasta de sua página ou de seu componente proprietário; componentes com consumidores independentes vão para `components`.

Preservar React, JavaScript/JSX, Vite, CSS, rotas, contratos da API, regras financeiras e aparência atual durante a extração. Migrações de linguagem, bibliotecas e redesenho visual são decisões posteriores.

## 2. Diagnóstico do código atual

As quantidades abaixo são do código local avaliado. Linhas ajudam a localizar concentração de responsabilidades, mas não serão uma meta artificial de qualidade.

| Arquivo | Observação concreta | Encaminhamento |
| --- | --- | --- |
| `frontend/src/pages/ExpensesPage.jsx` — 573 linhas | Reúne `ExpenseForm`, `IncomeForm`, `ExpenseList`, lista de entradas, validações, payloads, consultas, exclusões e coordenação da tela. | Extrair os três componentes já compartilhados; manter a lista de entradas junto da página; separar lógica dos formulários e operações do cache. |
| `frontend/src/pages/ExpenseHistoryPage.jsx` — 147 linhas | Importa `ExpenseForm`, `ExpenseList` e `IncomeForm` diretamente de `ExpensesPage.jsx`, na linha 8. Também interpreta URL, consulta dados e controla edição. | Eliminar dependência entre páginas. Manter `HistoryFilters` e a coordenação do histórico na pasta desta página. |
| `frontend/src/pages/ReportsPage.jsx` — 296 linhas | Mistura serialização de filtros, rascunho de período, consultas, retenção de resultado anterior, total e composição de gráficos. | Separar filtros, lógica da página, apresentação do resumo e gráficos locais. |
| `frontend/src/pages/SettingsPage.jsx` — 210 linhas | `CatalogSection` já reaproveita os três tipos de cadastro, mas reúne formulário, estado, mutações, listagem e diálogo. | Preservar a abstração existente e separá-la internamente, próxima de SettingsPage. |
| `frontend/src/pages/AuthPage.jsx` — 208 linhas | Formulário local e fluxo Google dividem o arquivo com listeners, timers, popup e validações de mensagens. | Isolar o fluxo Google em hook local e separar os blocos visuais da autenticação. |
| `frontend/src/main.jsx` — 124 linhas | Inicializa React e também define layout, navegação, proteção de rotas, destinos de login e seleção de páginas. | Deixar o bootstrap em `main.jsx`; composição e rotas em `App.jsx`; layout e estado em seus respectivos módulos. |
| `frontend/src/services/api.js` — 181 linhas | Centraliza corretamente o transporte, mas também reúne endpoints de todos os domínios. | Manter um único cliente HTTP e separar serviços por domínio sem duplicar refresh, timeout ou erros. |
| `frontend/src/shared/queryCache.js` — 267 linhas | Cache global, adaptação para React e apresentação de mensagens de erro estão no mesmo módulo. | Mover o cache para `store`, separar seu hook e deixar mensagens reutilizáveis em helper sem React. |
| `frontend/src/shared/useExpenseLookups.js` — 57 linhas | Cada uso assina seis consultas: categorias de despesas, meios de pagamento e categorias de entradas, nas versões ativa e histórica. | Criar hooks de referência específicos; cada consumidor assina apenas o que precisa. O cache continua deduplicando consumidores iguais. |
| `frontend/src/styles.css` e `viewport.css` — 655 + 207 linhas | Estilos de várias telas e componentes se misturam; há dois blocos `:root` e sobrescritas posteriores de layout. | Consolidar valores globais e distribuir regras por proprietário, conferindo a cascata e a rolagem. |

Há **37 ocorrências de `<button>`, 9 de `<select>` e 20 de `<input>`** nos arquivos JSX. A contagem é de marcações no código, incluindo componentes já existentes; não corresponde ao número de elementos exibidos simultaneamente. Ela mostra a oportunidade de padronização, sem justificar uma substituição mecânica de todas as tags.

### O que já está bem encaminhado

- `Panel`, `SectionHeading`, `SectionSwitcher`, `EmptyState`, `Icon`, `CategoryIcon` e `DebouncedSearchField` já são reaproveitados. Evoluí-los, em vez de criar alternativas paralelas.
- `ExpenseForm`, `IncomeForm` e `ExpenseList` já têm consumidores reais em duas páginas. Sua promoção para `components` é imediata e justificada.
- `CatalogSection` já evita repetir três CRUDs semelhantes. Sua reutilização é interna a SettingsPage e não exige promoção global.
- `shared/format.js` já concentra formatadores de moeda e calendário e reutiliza instâncias de `Intl`.
- O cache já implementa deduplicação, cancelamento, invalidação e proteção na troca de sessão. Sua reorganização deve preservar essas garantias.
- As páginas de negócio já são carregadas sob demanda. Manter esse comportamento e eliminar importações de uma página por outra.

### Acoplamentos e inconsistências que precisam de atenção

1. `ExpensesPage.jsx` importa `categoryColor` de `CategoryChart.jsx`. Uma lista depende de um módulo de gráfico para obter uma cor. Extrair a função e a paleta para um módulo compartilhado sem JSX; o gráfico pode então ficar local em ReportsPage.
2. `validMonth` e padrões de filtros ativos se repetem em histórico e relatórios. Compartilhar validação de mês, identificação das referências e apresentação das etiquetas; manter a definição dos filtros de cada rota local.
3. A validação do destino após login está em três lugares. `main.jsx` permite `/configuracoes`, mas AuthPage e GoogleAuthComplete não. Centralizar a política e cobrir o retorno a essa rota, sem ampliar destinos para URLs arbitrárias.
4. Exclusão de despesas e cadastros usa `<dialog>`, enquanto a exclusão de entradas usa `window.confirm` e `window.alert`. Padronizar com o mesmo componente de confirmação, preservando mensagens próprias de cada operação.
5. O estado de sucesso e erro dos formulários não segue um padrão único. Especialmente em IncomeForm, ambos usam a mesma mensagem com `role="status"`. Separar os tipos de retorno ao adotar o componente compartilhado.
6. `CURRENT_MONTH` é calculado no carregamento do módulo de ExpensesPage. Definir e verificar o comportamento ao atravessar a virada do mês com a aplicação aberta; apenas mover a constante não resolve isso.

## 3. Componentes que vale reaproveitar

### Controles e padrões visuais

| Componente | Contrato inicial | Consumidores identificados |
| --- | --- | --- |
| `Button` | `variant`, `size`, `loading`, `disabled`, `type`, `children` e atributos nativos. `type="button"` por padrão; envio explícito com `type="submit"`. Carregamento bloqueia novo acionamento e é anunciado. | Formulários, filtros, paginação, configurações e saída da conta. |
| `IconButton` | Compõe Button; exige nome acessível; recebe ícone e ação. `title` pode complementar o rótulo. | Editar/excluir despesas, entradas e cadastros. |
| `FormField` | Rótulo, ID, ajuda, erro e controle filho; associa `label`, `aria-describedby` e `aria-invalid`. Evitar duplicar essas responsabilidades em Input e Select. | Formulários e filtros. |
| `Input` | Aparência e atributos nativos, incluindo `type`, `inputMode`, `autoComplete`, limites e referência ao elemento para foco. | Descrição, nome, e-mail, senha, datas e meses. |
| `Select` | Controle nativo com `value`, `onChange`, `children`, `disabled`, `required`, referência e atributos de acessibilidade. | Categorias, meios de pagamento e tipos de valor parcelado. |
| `MoneyInput` | Compõe Input e prefixo monetário; preserva a máscara e o contrato textual do valor. Não calcula parcelas nem chama API. | ExpenseForm e IncomeForm. |
| `FeedbackMessage` | Tipo `success`, `error` ou `info`; mensagem e semântica de anúncio apropriada. | Formulários e operações. |
| `QueryFeedback` | Estados de carga inicial, erro, atualização e nova tentativa. A decisão de reter dados anteriores pertence ao consumidor. | Listas, relatórios e cadastros. |
| `ConfirmDialog` | Título, descrição, conteúdo, confirmação/cancelamento e estado pendente. IDs únicos, foco inicial seguro, retorno de foco e tratamento de Escape. | Despesas, entradas e cadastros. |
| `ActiveFilters` | Lista de etiquetas com identificador, texto e callback de remoção. | Relatórios e histórico. |
| `FinancialSummaryCard` | Título, valor, detalhamento e estado visual; recebe totais prontos. | Resumo do mês e do consolidado. |

Começar por Button, IconButton, FormField, Input e Select. Os demais entram quando seus consumidores forem migrados, para que a API de cada componente nasça de necessidades concretas.

O Select genérico não sabe o que é categoria, referência excluída ou meio de pagamento. A preparação das opções fica no domínio ou em helper apropriado; FormField cuida do rótulo. Não adicionar busca, seleção múltipla ou um menu customizado sem requisito.

Evitar um Button com dezenas de booleanos como `isDelete`, `isGoogle`, `isFilter` e `isSubmit`. Variantes visuais pequenas e composição atendem melhor. Um botão Google exclusivo continua junto da autenticação e compõe Button quando isso ajudar.

### Componentes de negócio

- **ExpenseForm e IncomeForm:** compartilhados entre cadastro e histórico. Cada um terá seu hook local para campos, validação, envio e mensagens; regras de despesas e entradas continuam separadas.
- **ExpenseList:** manter o nome durante a primeira extração. Ele já lida com cobranças e reembolsos; avaliar depois o nome `ExpenseMovementList`. O item visual e a confirmação ficam dentro de sua pasta enquanto só ele os usar.
- **MonthlyIncomeList:** usada apenas em ExpensesPage; fica próxima da página. Pode compartilhar IconButton e ConfirmDialog sem forçar uma lista genérica para todos os domínios.
- **ReportFilters e HistoryFilters:** continuam distintos. Reutilizam controles, busca e etiquetas; período com aplicação explícita e mês único têm comportamentos diferentes.
- **MonthlyChart e CategoryChart:** hoje só são renderizados em ReportsPage; passam para sua pasta depois da extração de `categoryColor`.
- **CatalogSection:** permanece dentro de SettingsPage. Extrair um hook local se necessário; não criar um framework de CRUD configurável para o restante da aplicação.

## 4. Estrutura proposta

Árvore de destino ilustrativa. As pastas são criadas conforme a migração; não criar arquivos vazios para completar o desenho. Componentes movidos que ainda não precisam de CSS próprio podem receber `index.css` somente ao ganhar estilos locais.

```text
frontend/
  src/
    main.jsx                         # montagem do React e CSS global
    App.jsx                          # providers, rotas e composição de layouts
    index.css                        # tokens, reset, base e acessibilidade global
    components/
      Button/                        # index.jsx + index.css
      IconButton/
      FormField/
      Input/
      Select/
      MoneyInput/
      FeedbackMessage/
      QueryFeedback/
      ConfirmDialog/
      ActiveFilters/
      FinancialSummaryCard/
      Panel/
      SectionHeading/
      SectionSwitcher/
      EmptyState/
      DebouncedSearchField/
      Icon/
      CategoryIcon/
      AppLink/
      Footer/
      AppLayout/
        index.jsx
        index.css
        Header/                      # exclusivo deste layout
          index.jsx
          index.css
      ExpenseForm/
        index.jsx
        index.css
        useExpenseForm.js            # campos e coordenação local
        form.js                      # estado inicial, validação e payload
        form.test.js                 # testes unitários das regras do formulário
      IncomeForm/
        index.jsx
        index.css
        useIncomeForm.js
        form.js
      ExpenseList/
        index.jsx
        index.css
        useExpenseList.js
        ExpenseRow/
          index.jsx
          index.css
    pages/
      ExpensesPage/
        index.jsx
        index.css
        useExpensesPage.js
        MonthlyIncomeList/
          index.jsx
          index.css
      ExpenseHistoryPage/
        index.jsx
        index.css
        useExpenseHistoryPage.js
        filters.js
        HistoryFilters/
          index.jsx
          index.css
      ReportsPage/
        index.jsx
        index.css
        useReportsPage.js
        filters.js
        ReportFilters/               # index.jsx + index.css
        MonthlyChart/
        CategoryChart/
      SettingsPage/
        index.jsx
        index.css
        catalogs.js                  # títulos e configuração visual local
        CatalogSection/
          index.jsx
          index.css
          useCatalogSection.js
      AuthPage/
        index.jsx
        index.css
        useGoogleSignIn.js
        CredentialsForm/             # index.jsx + index.css
        GoogleSignInButton/
      GoogleAuthComplete/
        index.jsx
        index.css
    assets/
      brands/                        # por exemplo, SVG estático do Google
    services/
      httpClient.js                  # transporte, timeout, erros e refresh
      auth.js                        # operações de autenticação
      expenses.js                    # endpoints de despesas e relatórios
      incomeEntries.js
      catalogs.js
    shared/
      format.js
      money.js                       # parse e aritmética exata reutilizados
      money.test.js                  # testes unitários de valores e limites
      dates.js                       # validações comuns de calendário
      references.js                  # opções históricas e rótulos excluídos
      categoryColors.js
      routes.js                      # rotas e política pura de destino seguro
      errors.js
    store/
      auth/
        AuthProvider.jsx
        useAuth.js
      navigation.js                  # History API e assinatura de localização
      queryCache.js                  # núcleo do cache compartilhado
      useApiQuery.js                 # adaptação do cache para React
      queryKeys.js                   # chaves por conta, domínio e filtros
      queries/
        useCategories.js
        usePaymentMethods.js
        useIncomeCategories.js
        useMonthlyExpenses.js
        useIncomeEntries.js
        useExpenseHistory.js
        useExpenseSummary.js
      mutations/
        expenses.js                  # operação + invalidação do cache
        incomeEntries.js
        catalogs.js
  tests/
    queryCache.test.js               # ajustar imports quando o cache mudar
```

Para novos componentes, preferir nomes de pastas em PascalCase e imports explícitos como `../components/Button/index.jsx`. Helpers e hooks usam nomes descritivos em camelCase. Não criar um `components/index.js` que reexporta toda a aplicação; os `index.jsx` acima são a implementação de cada componente.

Testes unitários ficam junto do módulo testado, com nomes `*.test.js` ou `*.test.jsx`; os dois exemplos da árvore não limitam a cobertura exigida. A pasta `frontend/tests` pode manter as suítes existentes e testes de integração entre módulos.

Não proponho substituir a estrutura solicitada por uma arquitetura de `features`. A organização por página e a proximidade dos arquivos já atendem bem ao porte atual.

### Fronteiras entre as pastas

| Área | Responsabilidade | Limite |
| --- | --- | --- |
| `pages` | Composição da rota, estado exclusivo da tela e componentes locais. | Uma página não importa outra página; não concentra marcação de blocos inteiros nem implementação de transporte. |
| `components` | UI compartilhada e blocos de negócio usados por consumidores independentes. | Primitivas visuais não acessam API, sessão ou cache; componentes de negócio delegam efeitos aos seus hooks. |
| `assets` | Arquivos estáticos. | Ícones dinâmicos em JSX continuam sendo componentes; não precisam virar arquivos de imagem. |
| `services` | Comunicação externa e adaptação de contratos HTTP. | Não renderiza JSX, não contém hooks nem invalida cache da UI. |
| `shared` | Funções e valores reutilizados sem React: formatação, validação e transformação. | Não vira depósito de componentes, providers, estado global ou efeitos de navegador. |
| `store` | Sessão compartilhada, localização, cache, assinaturas e operações que o atualizam. | Não recebe estado dos campos dos formulários nem copia os mesmos resultados para outro estado global. |

Dependências principais: página → componentes/hooks locais → consultas/mutações do store → services → transporte. Helpers de shared podem ser usados por essas camadas, sem importar as camadas superiores. A composição dos providers fica em App.

O cliente HTTP mantém detalhes internos de transporte, como token em memória e deduplicação do refresh. Ele não importa o provider de autenticação nem módulos do store. O store consome o cliente; a notificação de sessão expirada pode preservar o contrato de evento existente. Isso evita um ciclo entre cliente HTTP, serviço de autenticação e provider.

## 5. Estado, consultas e formulários

Separar quatro tipos de estado:

1. **Local:** texto digitado, erro de campo, envio em andamento, diálogo aberto, item em edição e seção ativa no celular. Fica no componente proprietário ou em seu hook local.
2. **URL:** filtros aplicados e paginação. A URL permanece a fonte de verdade; rascunho de período e busca antes do debounce são estados locais temporários.
3. **Servidor:** despesas, entradas, referências e resumos. Ficam no cache em `store`, sem cópia em um segundo contexto ou array global.
4. **Sessão:** usuário, status de autenticação e transições de login/logout. Fica no provider; tokens mantêm a política atual de armazenamento.

Hooks compartilham lógica; suas chamadas não passam a compartilhar automaticamente os campos de um formulário. Um hook de formulário fica próximo do formulário mesmo quando ele é reutilizado.

No lugar de `useExpenseLookups`, os consumidores passam a selecionar referências por necessidade: `useCategories({ includeDeleted: true })`, por exemplo. A identidade da conta pode ser lida pelo hook de consulta; a chave gerada sempre inclui o ID do usuário. A tela de relatórios não precisa assinar categorias de entrada para desenhar seus filtros.

Centralizar chaves e operações de invalidação para que componentes não precisem conhecer vários prefixos de cache. Manter explícitas as relações:

- Despesa criada, editada ou excluída → pagamentos, histórico e resumo de despesas.
- Entrada/reembolso alterado → listas de entradas, histórico e resumo financeiro afetados.
- Cadastro alterado → referências ativas/históricas e consultas financeiras que exibem seus rótulos ou regras.
- Logout/troca de conta → cancelar requisições e limpar cache; respostas anteriores não podem repovoá-lo.

Preservar validade de 30 minutos para referências, 2 minutos para resultados e retenção inativa atual de 5 minutos. A extração não acrescenta polling, consultas por foco nem novas políticas de retry.

Separar também transformação de dados de seus efeitos: `validateExpenseForm` e `toExpensePayload`, por exemplo, não fazem requisições nem alteram cache. As operações compartilhadas em `store/mutations` coordenam serviço e invalidação; o hook local controla mensagens e estado pendente do formulário.

## 6. CSS e consistência visual

- Usar um único conjunto de tokens globais: cores, tipografia, espaçamento, bordas, raios, sombras e duração de transições. Consolidar os valores efetivos atuais, sem reintroduzir valores sobrescritos.
- Deixar reset, estilos básicos, foco visível e movimento reduzido em `src/index.css`.
- Mover regras de Button, Select, Panel e outros componentes para seus próprios `index.css`; páginas recebem só a composição e o layout específicos.
- CSS comum importado por componentes continua global. Usar classes próprias, como `.button`, `.expense-form` e `.reports-page`, com descendentes delimitados; o nome `index.css` sozinho não oferece isolamento.
- Remover dependência da ordem em que páginas lazy são visitadas. Nenhuma página redefine tokens globais ou regras genéricas de outra tela.
- Redistribuir `viewport.css` por proprietário só depois de conferir suas regras de altura, `min-height`, overflow e rolagem. Não simplesmente apagar o arquivo ou copiar todas as regras para outro CSS global.
- Preservar os alvos de toque, telas de edição, tabelas acessíveis dos gráficos e `prefers-reduced-motion`. A preferência por não usar verde continua valendo no tema.

## 7. Achado funcional a tratar separadamente

**Subtotal negativo com centavos:** `sumInstallmentAmounts`, em `ExpensesPage.jsx:57`, divide e calcula o resto de um BigInt negativo ao montar uma string decimal. A reprodução isolada com a função atual e `formatMoney` confirmou:

| Dados da lista | String produzida | Exibição atual | Resultado esperado |
| --- | --- | --- | --- |
| Um reembolso de R$ 1,50 | `-1.-50` | R$ 0,00 | -R$ 1,50 |
| Um reembolso de R$ 0,50 | `0.-50` | R$ 0,00 | -R$ 0,50 |
| Um reembolso de R$ 2,00 | `-2.00` | -R$ 2,00 | -R$ 2,00 |

O achado se refere ao subtotal calculado no frontend para a lista; não demonstra erro nos totais devolvidos pela API nem nos valores armazenados. Criar correção pequena e identificável: separar sinal e magnitude ao serializar centavos, com testes para positivos, negativos, zero e mistura de cobranças/reembolsos. Não preservar esse defeito como requisito da refatoração.

A política de destino após login e a virada do mês também merecem testes e decisões explícitas. Mudanças de comportamento devem aparecer como correções próprias, sem ficarem escondidas em uma movimentação de arquivos.

## 8. Ordem de execução e critérios de aceite

Cada fase deve deixar a aplicação utilizável e permitir revisão e reversão isoladas. Evitar uma única alteração que mova todos os arquivos e simultaneamente troque bibliotecas, comportamento e CSS.

| Fase | Entrega | Critério de aceite |
| --- | --- | --- |
| 0 — Base de comparação e testes | Registrar rotas, aparência desktop/celular, requisições e fluxos críticos; executar testes existentes e build; configurar ambiente e comando de testes unitários para funções, hooks e componentes React. | Execução unitária disponível antes das extrações; resultados reais registrados e comportamentos atuais identificados. Separar correção do subtotal negativo com teste de regressão antes de adotá-la como referência. |
| 1 — Controles básicos | Criar Button, IconButton, FormField, Input e Select; migrar controles de SettingsPage e selects dos filtros do histórico como primeiros consumidores. | Teclado, foco, envio explícito, pendência e erros funcionam; não há requisições extras nem mudança visual inesperada. |
| 2 — Componentes de negócio | Extrair ExpenseForm, IncomeForm e ExpenseList; manter assinatura e comportamento inicialmente. Extrair lista de entradas local. | ExpenseHistoryPage deixa de importar ExpensesPage; cadastro e edição continuam funcionando nos dois contextos. |
| 3 — Lógica e dados | Separar cliente HTTP/serviços, cache/hook, referências específicas e operações de invalidação; extrair lógica local dos formulários. | Sem importações circulares; mesmas garantias de sessão/cache; controles visuais sem dependência do transporte. |
| 4 — Páginas e navegação | Migrar páginas para suas pastas; extrair filtros, lógica de relatórios, fluxo Google, layout e composição de App. Centralizar destinos seguros em alteração identificável. | Páginas descrevem a composição; lazy loading, acesso direto, voltar/avançar e retorno de autenticação funcionam. |
| 5 — Padrões e estilos | Migrar ConfirmDialog, mensagens, etiquetas, resumo financeiro e CSS por proprietário. | Exclusões consistentes, sem perda de foco, sem vazamento de estilos entre rotas ou regressão na rolagem. |
| 6 — Consolidação | Remover arquivos/exports antigos, atualizar documentação e scripts de verificação; configurar lint e formatação proporcionais ao projeto. | Um caminho oficial para cada abstração; imports e checks passam; instruções correspondem aos comandos disponíveis. |

As fases 2 a 5 podem ser divididas por tela. Mover CSS junto do componente somente quando seu comportamento puder ser conferido; manter os estilos antigos temporariamente é aceitável, mas cada fase deve indicar o que será removido depois.

**Critério obrigatório em todas as fases de implementação:** criar ou atualizar os testes unitários das regras e comportamentos relevantes dos módulos afetados, preservar a cobertura existente e executar a suíte pertinente com sucesso antes de concluir a etapa. Mover arquivos exige ajustar também os imports dos testes. Build e revisão visual complementam os testes unitários.

### Testes unitários obrigatórios

A refatoração deve incluir testes unitários desde a primeira etapa de implementação. A cobertura precisa proteger contratos e resultados observáveis, com prioridade para:

- **Dinheiro:** máscara, normalização e validação de entradas; soma exata de centavos; valores positivos, negativos e zero; regressão do subtotal negativo com centavos.
- **Datas e filtros:** validação de mês, limites de intervalo, filtros padrão, leitura e serialização da URL e política de destino seguro após autenticação.
- **Formulários:** estado inicial, dados de edição, validações, construção dos payloads, regras de parcelamento, vínculo de reembolsos e manutenção de referências excluídas permitidas.
- **Hooks com comportamento próprio:** mudanças de estado, envio pendente, sucesso, falha, preservação dos campos e cancelamento/limpeza de timers e listeners quando aplicável.
- **Cache e coordenação:** chaves por usuário e filtros, deduplicação, invalidação, cancelamento e proteção contra respostas de sessões anteriores, preservando os testes existentes.
- **Componentes com comportamento:** tipo e bloqueio de Button, callbacks, associação entre campo e erro, Select controlado e confirmação/cancelamento de diálogos. Não criar testes triviais para componentes que apenas repassam marcação.

Os testes devem ser rápidos, isolados e determinísticos, sem API, banco de dados ou credenciais reais. Controlar relógio e timers nos cenários temporais e simular respostas externas nas fronteiras necessárias, sem substituir a própria regra que está sendo verificada. Correções de defeitos devem incluir teste de regressão que reproduza o erro e valide o resultado correto.

Na fase 0, configurar a execução dos testes de React com ambiente de DOM e adicionar o script correspondente ao `package.json`. O runner Node existente pode continuar cobrindo funções puras e o núcleo do cache; a execução documentada deve contemplar ambas as suítes. Não adiar essa infraestrutura para a fase final.

### Verificação proporcional ao risco

Comandos existentes, executados a partir de `frontend`:

```powershell
node --test tests/queryCache.test.js
pnpm build
```

O `package.json` atual só declara `dev`, `build` e `preview`: ainda não há `pnpm test`, `pnpm lint` ou `pnpm format`. Acrescentar os scripts correspondentes quando suas ferramentas forem configuradas. Não registrar comandos inexistentes como validação concluída.

Além dos testes unitários obrigatórios, verificar a integração dos fluxos e a interface conforme os riscos de cada mudança:

- Botões de formulário: ação comum não envia; envio explícito funciona; estado pendente impede repetição.
- FormField/Select: rótulo, erro associado, navegação por teclado, foco e opções indisponíveis.
- Despesas: criação/edição à vista e parcelada; payload e mensagens preservados; falha mantém os campos.
- Entradas: reembolso exige categoria de despesa; entrada comum não envia esse vínculo.
- Referências excluídas: disponíveis no histórico e preservadas na edição antiga; não entram em novo cadastro.
- Histórico/consolidado: URL, debounce de 400 ms, paginação, aplicação do período e identificação dos dados anteriores durante atualização/falha.
- Sessão: login local, cadastro, Google por popup e redirecionamento, popup bloqueado, origem/janela/identificador de mensagem, destino permitido, logout e resposta tardia de outra sessão.
- Diálogos: confirmar, cancelar, falha, estado pendente, Escape, rótulos únicos e retorno do foco.
- Calendário e dinheiro: subtotal negativo com centavos, datas sem mudança de dia e comportamento na virada do mês.
- CSS: navegação entre rotas em ordens diferentes, desktop e celular, edição, conteúdo longo, erro de API e movimento reduzido.

Os testes unitários de componentes React devem usar a infraestrutura prevista na fase 0. Testes de integração e revisão visual complementam a cobertura dos fluxos acima; uma suíte completa de ponta a ponta pode ser planejada conforme a necessidade. Backend só exige nova execução da suíte quando houver mudança de contrato ou comportamento de integração que a justifique.

### Estado da validação nesta avaliação

- Leitura estática de todas as páginas, infraestrutura, componentes e estilos do frontend.
- **5 testes existentes de cache passaram**, executados com o Node disponível no runtime local.
- Reprodução isolada do defeito do subtotal, sem requisições ou alterações em dados.
- Build e revisão visual da aplicação não foram executados nesta etapa de documentação. A tabela de fases descreve verificações futuras, não entregas já implementadas.

## 9. Melhorias adicionais e limites da proposta

- Tornar as APIs dos componentes previsíveis: atributos HTML preservados, composição por `children`, referências para foco e variantes pequenas. Usar JSDoc nos contratos mais importantes pode ajudar sem exigir migração de linguagem.
- Configurar lint com verificação das regras de hooks e formatação consistente; priorizar código novo e alterado, evitando um diff de formatação de todo o projeto junto da extração.
- Revisar o uso de `latest` no `package.json` e adotar versões declaradas de forma controlada, coerentes com o lockfile. Fazer isso em manutenção própria, sem atualizar dependências incidentalmente durante a refatoração.
- Manter o cache e a navegação atuais nesta primeira etapa. Reavaliar bibliotecas especializadas quando a manutenção dessas infraestruturas justificar o custo de migração; a pasta `store` não implica instalar Redux ou Zustand.
- Tratar TypeScript, biblioteca de formulários, CSS Modules e biblioteca de UI como opções futuras. Nenhuma é pré-requisito para resolver a concentração de responsabilidades identificada.
- Evitar metas rígidas de linhas, memoização automática e componentes genéricos sem consumidores concretos. O aceite é entender responsabilidades, preservar comportamento e reduzir duplicação real.

## 10. Referências técnicas

As decisões de fronteira acima são propostas para este repositório; não são uma estrutura de pastas obrigatória do React.

- [React — Thinking in React](https://react.dev/learn/thinking-in-react): decomposição da interface e responsabilidade dos componentes.
- [React — Reusing Logic with Custom Hooks](https://react.dev/learn/reusing-logic-with-custom-hooks): extração de lógica e distinção entre reutilizar lógica e compartilhar estado.
- [MDN — button](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/button): tipo de botão e nome acessível em ações com ícones.
- [MDN — select](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/select): controle de seleção nativo e associação com rótulos.
