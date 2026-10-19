# Plano de evolução do frontend

Data: 19/10/2026. Status: implementação concluída na branch `feat/frontend-navigation-consolidated`. A suíte do backend passou; não foi possível executar o build frontend neste shell porque Node.js e pnpm não estavam instalados no PATH.

## Objetivo e decisões confirmadas

Criar uma navegação simples entre cadastro de despesas e gastos consolidados, preservando a identidade visual atual. A implementação deve reaproveitar componentes, funções e consultas, limitar renderizações desnecessárias e evitar chamadas redundantes à API.

Decisões confirmadas pelo usuário nesta conversa:

- O consolidado considera o valor de cada parcela no mês da cobrança, conforme a regra atual da API.
- A lista ao lado do cadastro mostra as últimas compras cadastradas, uma linha por compra, com indicação do parcelamento.

Manter interface em português, moeda em reais, cores leves, transições suaves e a proibição de verde registrada no `CONTEXTO.md`.

## Situação observada antes da implementação

- `frontend/src/App.jsx` concentra layout, formulário, lista e estado. Header e Footer já existem como marcação e estilos; devem ser extraídos e adaptados.
- O frontend usa React, Vite e CSS, com despesas em memória e categorias fixas. Ainda não há integração com a API, roteador, biblioteca de gráficos ou biblioteca de consultas.
- O formulário atual não contempla meio de pagamento nem parcelamento. Descrição aceita 80 caracteres, enquanto a API aceita 120.
- `GET /expenses` lista cobranças paginadas, ordenadas por vencimento decrescente. Seus filtros atuais são `month` e `search`. Não atende diretamente ao requisito de últimas compras cadastradas.
- `amount_due` representa a cobrança; `total_amount` representa a compra inteira. O campo de paginação `total` conta cobranças e não é um valor monetário.
- Os controllers de categorias e meios de pagamento ainda não expõem GET, mas os serviços de listagem e schemas de resposta já existem e podem ser reutilizados.
- Existe `backend/app/seed.py`, inclusive com a categoria Mercado. Sua execução e o conteúdo atual do banco não foram verificados nesta etapa. A observação complementa o contexto, que menciona ausência de seed nas migrações.
- O frontend não declara testes; o backend possui uma suíte para os fluxos existentes. O planejamento foi baseado nos arquivos locais, sem consultas ao banco ou alterações de dados.

## Telas e navegação

| Elemento | Comportamento proposto |
| --- | --- |
| Header | Reaproveitar a marca atual; clicar nela leva ao cadastro. |
| Navbar | Dois links: Cadastro de despesas e Gastos consolidados, com indicação da rota ativa e foco visível. |
| Footer | Reaproveitar o texto e o estilo atuais; ano obtido dinamicamente. |
| `/despesas` | Formulário e últimas compras lado a lado em telas largas; formulário acima da lista no celular. |
| `/consolidado` | Filtros, total do período, evolução mensal e distribuição por categoria. |
| `/` | Redirecionar para `/despesas`. |

Header, Navbar e Footer pertencem a um layout compartilhado. Somente o conteúdo principal muda entre rotas. A navegação deve funcionar sem recarregar a página, incluindo os botões voltar/avançar e acesso direto à URL. Prever uma mensagem simples para endereço inexistente e a configuração de fallback para `index.html` na hospedagem futura.

Esboço da organização em telas largas:

```text
Header: expenses.
Navbar: Cadastro de despesas | Gastos consolidados

/despesas                     /consolidado
Título                        Título
Formulário | Últimas compras   Filtros
                              Total do período
                              Evolução mensal
                              Gastos por categoria

Footer compartilhado
```

## Cadastro e últimas compras

Preservar o padrão visual do formulário e da lista atuais, extraindo componentes antes de ampliar os campos.

- Manter descrição, valor, data e categoria; adicionar meio de pagamento, exigido pela API.
- Categorias e meios de pagamento vêm de seus respectivos GETs, usando IDs no envio. Nenhum ID deve ser fixado no frontend.
- Expor à vista/parcelado; quando parcelado, mostrar quantidade, entrada por valor total ou da parcela e data da primeira cobrança. Reaproveitar as regras já implementadas no backend e no plano de parcelamentos.
- Validar campos no navegador para dar retorno imediato e apresentar também as mensagens de erro da API. O backend continua sendo responsável pelo cálculo e cronograma definitivos.
- Bloquear envio duplicado enquanto a gravação estiver pendente. Em falha, preservar os valores digitados; limpar o formulário somente após sucesso.
- Proposta inicial: mostrar as 10 últimas compras, ordenadas por `created_at DESC, id DESC`, usando `expense.id` como chave. Uma compra antiga registrada hoje aparece entre as recentes.
- Cada item mostra descrição, categoria, data da compra, total e indicação de pagamento à vista ou parcelado. Não apresentar todas as parcelas como compras diferentes.
- Preservar exclusão com aviso claro de que ela remove a compra e todas as parcelas, conforme a regra existente.
- O total geral atualmente calculado com o array em memória passa para o consolidado, com período explícito. Não somar somente as 10 compras recentes e apresentar isso como total geral.
- Substituir o aviso de dados temporários quando a integração com a API estiver funcionando. Se não houver categorias ou meios de pagamento, explicar o estado e impedir um cadastro inválido.

## Consolidado, filtros e gráficos

Proposta inicial de filtros: intervalo de meses, categoria, meio de pagamento e busca textual. Intervalo, categoria e meio de pagamento são ampliações necessárias do contrato atual; mês e busca já existem no backend.

- Período padrão proposto: últimos 12 meses, incluindo o mês atual inteiro. Atalhos para mês atual, últimos 3, 6 e 12 meses, além de início/fim personalizados por mês.
- Categoria e meio de pagamento oferecem a opção Todos e seleção de um item por vez.
- Busca mantém o significado atual da API: descrição, categoria e meio de pagamento, sem diferenciar maiúsculas e minúsculas.
- Todos os filtros afetam o total e os dois gráficos. Alterações válidas são aplicadas automaticamente; a busca espera cerca de 400 ms sem digitação.
- Alterar início/fim como um par válido, sem consultar com intervalo invertido ou um campo incompleto. O botão Limpar filtros restaura os padrões em uma única atualização.
- Manter filtros aplicados na URL para preservar navegação, recarga e compartilhamento. Normalizar os parâmetros antes da primeira consulta para evitar uma busca inicial seguida de outra corretiva.

| Visualização | Informação e interação |
| --- | --- |
| Total do período | Soma exata das cobranças que correspondem aos filtros, independente de paginação. |
| Evolução mensal | Gráfico de linha com valor por mês, em ordem cronológica. Ao selecionar Mercado, mostra sua evolução no período. |
| Distribuição por categoria | Barras horizontais para comparar os valores das categorias no mesmo recorte. Uma categoria selecionada resulta em uma barra. |

Exemplo de aceite: ao selecionar Mercado e janeiro a junho de 2026, os seis meses aparecem no gráfico; uma compra de R$ 600 em 3 parcelas com primeira cobrança em fevereiro contribui com R$ 200 em fevereiro, março e abril. O total da compra não é repetido em cada mês.

Meses sem cobranças entram como zero quando a consulta for bem-sucedida. Um recorte totalmente vazio recebe uma mensagem adequada. Falha na API deve aparecer como erro, nunca ser convertida em gasto zero. Como não existe controle de pagamento realizado, os valores representam cobranças previstas; períodos futuros só entram quando selecionados.

## Responsividade, interação e animações

- Ajustar gráficos à largura disponível, com altura definida pelo painel e rótulos legíveis; reduzir a quantidade de rótulos visíveis no celular sem remover os dados.
- Mostrar mês/categoria e valor em reais ao passar o mouse, tocar ou navegar pelo teclado. Oferecer uma tabela acessível dos mesmos dados, sem nova consulta.
- Animar a atualização das séries e barras, com duração inicial de 300 a 500 ms e desaceleração suave. Validar o comportamento real ao mudar categoria e intervalo.
- Preservar a instância dos gráficos durante atualizações: não usar uma `key` baseada nos filtros para forçar remontagem.
- Usar meses e IDs de categorias como identificadores estáveis; manter uma cor estável para cada categoria. A linha conecta os valores registrados sem criar valores intermediários que sugiram gastos inexistentes.
- Na primeira carga, reservar espaço com um estado de carregamento. Nas mudanças seguintes, manter a visualização anterior visível e indicar Atualizando até receber o novo resumo.
- Enquanto os dados anteriores estiverem visíveis, identificar o recorte ao qual pertencem. Não apresentar valores antigos como resultado do novo filtro. Em falha, manter essa identificação e oferecer nova tentativa.
- Mudanças rápidas devem cancelar consultas obsoletas e transicionar para o último resultado. Hover, foco, redimensionamento e animação são interações locais e não disparam chamadas à API.
- Respeitar `prefers-reduced-motion` no CSS e na configuração das animações JavaScript dos gráficos.

## Reaproveitamento e organização do frontend

Manter JavaScript/JSX e CSS nesta entrega. Estrutura sugerida, ajustável durante a extração:

```text
frontend/src/
  app/                providers, rotas e AppLayout
  components/layout/  Header, Navbar e Footer
  components/ui/      Panel e estados compartilhados realmente usados
  features/expenses/  página, formulário, lista recente e funções de consulta/mutação
  features/reports/   página, filtros, gráficos e funções de consulta
  services/           cliente HTTP e consultas de categorias/meios de pagamento
  shared/             formatação monetária, datas e normalização de parâmetros
  styles.css          estilos existentes e variáveis visuais compartilhadas
```

Extrair os formatadores `Intl` e helpers de data atuais para funções compartilhadas; criar formatadores uma vez. Tratar datas sem horário como datas de calendário para evitar mudança de dia por fuso. Reaproveitar cores, espaçamentos, painéis e estados de interface através de variáveis CSS e componentes pequenos.

O estado dos campos fica dentro de `ExpenseForm`: digitar não deve atualizar a árvore da lista, do layout ou dos gráficos. Os filtros pertencem à tela de consolidado; dados vindos do servidor ficam no cache de consultas. Não manter cópias dos mesmos resultados em estados locais ou em um contexto global amplo.

Otimizar transformações e componentes caros quando houver benefício observado no React Profiler. `useMemo`, `useCallback` e `memo` são recursos pontuais; separar responsabilidades e manter dependências estáveis vem primeiro. Renderizações necessárias para mostrar novos dados e animar os gráficos fazem parte do comportamento esperado. Essa abordagem segue o uso de memoização como otimização descrito na [documentação do React](https://react.dev/reference/react/memo).

## Ferramentas usadas na implementação

| Escolha | Implementação |
| --- | --- |
| History API e um link compartilhado | Duas rotas, link ativo e navegação sem recarregar a página, sem instalar outra dependência. |
| Cache compartilhado com `useSyncExternalStore` | Deduplicação, cancelamento, atualização, repetição controlada e validade dos dados em `frontend/src/shared/queryCache.js`. Referências expiram após 30 minutos; compras e relatórios, após 2 minutos; entradas inativas são removidas após 5 minutos. |
| SVG, CSS e componentes React | Linha mensal com pontos consultáveis e tabela dos valores; comparação por categoria com barras que animam sua largura. Cálculos de totais permanecem no backend. |

O cliente HTTP usa `fetch` em `frontend/src/services/api.js`. Vite carrega cada tela sob demanda. A implementação não acrescentou dependências ao `package.json` nem modificou o lockfile.

## Política de consultas e cache

O cache próprio fica em um módulo compartilhado e reutilizável. Sua política implementada é:

| Dados | Chave lógica | Validade sem nova consulta | Retenção inativa |
| --- | --- | --- | --- |
| Categorias | `['lookups', 'categories']` | 30 minutos | 60 minutos |
| Meios de pagamento | `['lookups', 'payment-methods']` | 30 minutos | 60 minutos |
| Compras recentes | `['expenses', 'recent', {limit: 11}]`; a interface mostra 10 | 2 minutos | 5 minutos |
| Consolidado | `['expenses', 'summary', normalizedFilters]` | 2 minutos | 5 minutos |

As referências usam validade de 30 minutos e retenção inativa de 5 minutos.

- Consultar apenas o necessário à rota aberta. Os dois gráficos e o total leem a mesma resposta de resumo.
- Reutilizar o resultado de filtros já consultados enquanto estiver válido. Após expiração, a consulta pode ser renovada ao voltar à tela; expirar não implica polling.
- Desativar atualização por foco da janela e polling; permitir renovação de dados vencidos ao reconectar. Leituras podem repetir uma vez em erro de rede/servidor, sem repetição automática para erros de validação. Não repetir POST automaticamente.
- Propagar o `AbortSignal` até o `fetch` para interromper leituras obsoletas, conforme a [documentação de cancelamento](https://tanstack.com/query/latest/docs/framework/react/guides/query-cancellation). Uma resposta atrasada não pode substituir o recorte atual.
- Após cadastro bem-sucedido, usar a resposta completa para atualizar o cache recente existente, remover duplicidade e limitar o resultado armazenado a 11 compras. A tela apresenta as 10 primeiras. Leituras pendentes são canceladas para que uma resposta anterior não desfaça essa atualização.
- Invalidar os resumos de despesas após cadastro ou exclusão, incluindo recortes já armazenados. Resumos inativos aguardam a próxima visita para nova consulta. Não invalidar categorias ou meios de pagamento por alteração de despesas.
- Após exclusão, renovar o cache recente e o resumo. Usar o ID da compra no DELETE; tratar HTTP 204 sem tentar ler JSON.
- Não somar novamente no navegador todo o histórico ou carregar páginas em sequência para montar gráficos.

Expectativa em cache vazio e sem falhas: cadastro usa dois GETs de referências e um GET de recentes; consolidado usa as referências ainda ausentes e um GET de resumo. Filtros de data personalizados são aplicados juntos pelo botão **Aplicar período**; categoria e meio de pagamento são aplicados ao selecionar; a busca espera 400 ms. Trocar filtros estabilizados gera no máximo um GET de resumo quando não houver cache válido. Reutilizar o mesmo filtro válido, passar o mouse e redimensionar geram zero GETs. Submeter uma compra gera um POST e atualização local da lista; visitar o consolidado depois renova seu resumo invalidado.

Medir consultas em produção e distinguir requisições concluídas de cancelamentos durante o desenvolvimento com `StrictMode`. Preservar as verificações do React, corrigindo efeitos e dependências que provoquem trabalho redundante.

## Complementos mínimos no backend

Embora o objetivo seja o frontend, a API precisa oferecer os dados corretos para evitar processamento de histórico no navegador. Proposta dentro dos módulos existentes:

| Endpoint | Entrega |
| --- | --- |
| `GET /categories` | Reaproveita `list_categories` e `CategoryResponse`. |
| `GET /payment-methods` | Reaproveita `list_payment_methods` e `PaymentMethodResponse`. |
| `GET /expenses/recent?limit=11` | Lista limitada de compras únicas, com os campos de `ExpenseResponse`, ordenada por cadastro e ID decrescentes. A interface mostra as dez mais recentes. |
| `GET /expenses/summary` | Recebe `start_month`, `end_month`, `category_id`, `payment_method_id` e `search`; retorna total, valores mensais e valores por categoria do mesmo recorte. Limita o intervalo a 120 meses. |

Contrato sugerido para o resumo:

```text
filters: parâmetros normalizados do recorte retornado
total_amount_due: valor decimal em string
monthly_totals: [{month: "2026-01", amount_due: "200.00"}, ...]
category_totals: [{category_id: 1, amount_due: "600.00"}, ...]
```

Agregar no banco os valores de `ExpenseInstallment.amount` por mês de `due_date` e categoria, aplicando todos os filtros antes de agregar. Uma consulta agrupada pode alimentar as duas séries e o total no serviço, usando `Decimal`. Completar meses vazios no serviço com o mesmo calendário do intervalo. Não usar a soma de `Expense.amount`, nem uma página de `GET /expenses`, para obter o consolidado.

Reaproveitar a construção dos filtros de cobrança entre resumo e listagem. A listagem paginada passou a aceitar também intervalo de meses, categoria e meio de pagamento; as cobranças ainda usam suas datas de vencimento para filtrar.

Preservar as regras existentes de criação, divisão em centavos, datas e exclusão. No frontend, manter valores monetários como strings decimais ou centavos exatos; a conversão para número na biblioteca de gráficos serve à posição visual, sem substituir a soma oficial. Não criar migração apenas para reorganizar a interface. Avaliar índice para recentes caso a consulta e o volume justifiquem.

Definir a URL base da API em um único lugar, com proxy `/api` no Vite para o FastAPI e substituição via `VITE_API_BASE_URL` quando necessário. A interface depende das referências preparadas pelo seed existente; executá-lo ao configurar um banco novo.

## Ordem de implementação e validação

| Etapa | Entrega |
| --- | --- |
| 1. Estrutura visual | Concluída: layout compartilhado, duas rotas e páginas separadas. |
| 2. Contratos e consultas | Concluída: GETs de referências, recentes e resumo; filtros compartilhados e agregação. |
| 3. Cadastro conectado | Concluída: cliente HTTP, compra à vista ou parcelada, cache, lista e exclusão. |
| 4. Consolidado | Concluída: filtros na URL, total e gráficos a partir de um resumo. |
| 5. Acabamento e aceite | Estados de carga e erro, tabelas, teclado, movimento reduzido e layout responsivo implementados. Build do frontend ainda precisa ser executado num ambiente com Node.js e pnpm. |

O trabalho foi feito na branch `feat/frontend-navigation-consolidated`. `CONTEXTO.md`, `frontend/README.md` e `backend/README.md` foram atualizados. A branch ainda não foi enviada nem aberta como PR.

Validação feita e restante:

- Backend: 27 testes passam. Os novos testes cobrem busca e filtros combinados, resumo mensal com zeros, totais monetários e lista de compras únicas.
- Recentes: uma linha por compra parcelada, limite e ordenação de data de cadastro com desempate por ID testados.
- Frontend: não há suíte própria. Ainda faltam executar o build e fazer uma inspeção visual em navegador nas larguras de 320 px, tablet e desktop.
- Performance: digitar no formulário não atualiza a lista; hover e resize não consultam a API; mesma consulta válida é reutilizada; troca de filtro não remonta o gráfico; atraso de rede não provoca saltos no layout ou valores atribuídos ao filtro errado.
- Executar `pnpm build` e inspecionar as agregações em PostgreSQL caso o comportamento difira do SQLite usado na suíte. Node e pnpm não estavam disponíveis no shell desta execução.

Ficam fora desta entrega: edição visual de compras, administração de categorias, autenticação, exportação, metas, recorrências, faturas e controle de pagamento realizado. O cadastro e a exclusão atuais, os parcelamentos existentes e os gráficos solicitados compõem o escopo inicial.
