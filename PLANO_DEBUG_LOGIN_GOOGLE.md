# Plano de debug do login Google

Atualizado em 24/10/2026, horário de São Paulo.

## Resultado da investigação em 24/10/2026

**O login voltou a funcionar após o reinício do backend. O usuário confirmou: “Agora entrou”.**

- O JSON é de um cliente OAuth do tipo `web`. `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` do `backend/.env` coincidem exatamente com os valores do arquivo, sem expor credenciais. O callback `http://localhost:5173/api/auth/google/callback` consta nos redirecionamentos autorizados do JSON. `AUTH_FRONTEND_URL`, caminho e atributos locais dos cookies, `/api` e proxy estão alinhados; o frontend não contém segredos. Nenhum `.env` foi alterado.
- As três chaves locais têm 32 bytes em Base64; o par RSA conseguiu assinar e validar um JWT. O banco está na migração `20261022_0007`. A inspeção inicial encontrou zero identidades Google.
- O processo antigo em 8000 tinha PID 16228, iniciou às 01:11:05 e não usava recarga automática; o controller no disco tinha alteração às 01:16:06. O contrato servido já continha `result` e `request_id`, mas isso não comprovava que todas as alterações no disco estavam carregadas. O cancelamento simulado preservou o identificador e apagou o cookie corretamente.
- As tentativas reais anteriores registradas chegaram ao callback com código e estado, sem erro de autorização informado pelo Google. O backend antigo não produzia os avisos existentes no código atual. Não foi capturada a exceção interna de uma dessas tentativas; portanto, não é possível atribuir retrospectivamente a falha a uma exceção específica.
- A conectividade externa dos comandos restritos deste ambiente falhou, enquanto a mesma verificação com permissão de rede funcionou. No endpoint oficial do Google, credenciais reais com código deliberadamente inválido retornaram `invalid_grant`, sem `invalid_client`; a obtenção de chaves públicas pelo `PyJWKClient` também funcionou. Códigos de tentativas reais não foram reutilizados.
- O backend antigo foi encerrado e a versão do workspace foi iniciada com acesso à rede e sem log de URLs de requisição. O teste negativo passou a registrar `stage=token_exchange`, HTTP 400 e `invalid_grant`, comprovando que a instrumentação atual estava carregada e o Google era alcançável pelo servidor.
- Depois do reinício, a tentativa do usuário criou uma identidade Google e novas sessões; o usuário confirmou que entrou. **A recuperação operacional está comprovada. Código/ambiente do processo anterior eram diferentes, mas a participação isolada de cada diferença não foi demonstrada.** Não há evidência de erro nas credenciais fornecidas.

Foram adicionados diagnósticos para cookie ausente/inválido, metadados da tentativa, comparação de estado, autorização Google, ausência de código, troca do código, obtenção de chave, validação do ID token e criação da sessão. Os testes verificam também que os logs não expõem código, estado, cookie ou segredo. O inicializador passa a usar `--reload --reload-dir app --no-access-log`; alterações no `.env` continuam exigindo reinício explícito. O processo deixado em execução nesta rodada foi iniciado diretamente para o diagnóstico, sem recarga automática; as novas opções se aplicam às próximas inicializações pelo script.

Validação: **51 testes do backend aprovados** (incluindo 15 de autenticação), build de produção do frontend aprovado e login real confirmado pelo usuário. O controle do Chrome foi interrompido pela ferramenta por não conseguir determinar a URL atual com segurança; a tentativa real foi feita pelo usuário. Recarregamento da página, logout, fallback na mesma aba e renovação por expiração não foram acompanhados nesta rodada.

O restante deste documento preserva o plano e o histórico anteriores ao resultado acima.

## Situação e objetivo

O usuário confirmou que o login continua falhando após as correções de navegação e o reinício do frontend. A causa da falha ainda não foi comprovada. O objetivo desta rodada é identificar a primeira etapa que diverge do comportamento esperado em uma tentativa real, corrigir essa causa e confirmar a abertura e a continuidade da sessão.

Este documento atualiza o plano de debug discutido no chat. O histórico da implementação está em [PLANO_LOGIN_GOOGLE.md](PLANO_LOGIN_GOOGLE.md). A elaboração deste plano não inclui novas alterações no código nem reinícios de serviços.

## Tentativas realizadas e limites das evidências

| Verificação ou alteração | Resultado observado | O que ainda falta comprovar |
| --- | --- | --- |
| Presença das variáveis OAuth e das chaves locais | Variáveis preenchidas; valores secretos não foram expostos | Validade das credenciais no Google e configuração efetivamente usada pelo processo ativo |
| Status direto do backend e pelo proxy | Ambos retornaram HTTP 200 com `enabled: true` | O endpoint verifica presença das três variáveis Google; não valida credenciais, cookies ou o fluxo completo |
| Configuração local | Callback em `http://localhost:5173/api/auth/google/callback`, frontend em `http://localhost:5173`, cookie em `/api/auth`, `Secure=false` | Origem realmente aberta pelo usuário e atributos efetivos recebidos pelo navegador |
| Logs do backend | Inícios OAuth com 302 e callbacks com 303; existem chamadas de refresh com 401 | Resultado e motivo do callback, valores não sensíveis de `Location` e associação de cada chamada à mesma tentativa |
| Navegação da página de conclusão | `Root` passou a assinar mudanças de rota com `useLocation()` | Comportamento real do fallback pela mesma aba; essa correção não resolveu a falha relatada |
| Porta do Vite | Configurados `port: 5173` e `strictPort: true`; antes havia instâncias em 5173 e 5174 | Confirmação da origem da janela principal, popup e callback na tentativa com falha |
| Reinício do frontend | Duas instâncias anteriores encerradas; nova instância respondeu em 5173, com página e proxy retornando 200 | Login real após o reinício continua falhando, conforme relato do usuário |
| Testes e compilação | 12 testes de autenticação aprovados e build do frontend concluído | Integração real com Google, navegador, cookies e processos ativos; os testes não demonstram esse percurso |
| Acesso ao navegador na sessão de debug | Nenhum navegador disponível na ferramenta de controle na consulta anterior | Captura da tentativa real, incluindo a página de conclusão e os erros do Console |

No último trecho de log consultado, a sequência termina com refresh 401, consulta de status, início OAuth 302 e callback 303, sem refresh posterior nesse trecho. Um 401 anterior ao clique pode ser a verificação normal de uma sessão ausente. Um 303 também pode representar falha tratada, pois o controller atual redireciona tanto em sucesso quanto em erro. Esses registros, isoladamente, não demonstram que o Google autenticou nem que o cookie foi perdido.

## Hipóteses em ordem de investigação

1. **Backend em execução com uma versão diferente do contrato esperado pelo frontend.** O frontend atual depende de `result` e `request_id` no redirecionamento para `/auth/complete`. A implementação anterior redirecionava para essa rota sem esses parâmetros. O Uvicorn observado permaneceu com o mesmo PID durante as tentativas, foi iniciado sem `--reload` e não teve reinício confirmado nesta sequência. Isso torna a diferença de versões uma hipótese prioritária, ainda sem confirmação. Testes que importam o código atual não comprovam a versão carregada pelo servidor ativo.
2. **Cookie ou estado OAuth inválido antes da troca do código.** O callback pode retornar 303 com `reason=expired` antes dos pontos que hoje registram avisos. Ausência de warnings não elimina essa hipótese.
3. **Resultado do popup não recebido ou descartado pela janela principal.** Origem diferente, `request_id` ausente ou divergente, referência de janela incompatível ou isolamento de janelas podem impedir a chamada de refresh.
4. **Falha na troca do código, validação do token ou criação da sessão.** A presença de credenciais e o status 303 não eliminam problemas nessas etapas.
5. **Cookie de refresh rejeitado, não enviado ou sessão recusada.** Investigar quando houver evidência de callback bem-sucedido e de tentativa de confirmação da sessão.
6. **Falha depois do refresh.** Com refresh 200, separar erro de navegação, validação do access token ou carregamento de uma rota protegida.

## Execução proposta

### 1. Confirmar os processos e o contrato realmente servido

- Identificar o frontend em 5173 e o backend em 8000, com PID, horário de início, diretório do projeto e comando de inicialização, quando acessíveis.
- Comparar o início do backend com a data das alterações do controller e do service. Usar isso como indício; a resposta efetiva será a evidência principal.
- Na próxima tentativa real, capturar o `Location` do callback antes de seguir o redirecionamento. Registrar somente origem, caminho, `result`, `reason`, presença do `request_id` e sua correspondência com a tentativa.
- Conferir se o retorno segue o contrato atual: sucesso com `result=success` e identificador correspondente; erro com `result=error` e motivo controlado. Registrar explicitamente quando o cookie inválido impedir recuperar o identificador.
- Se a resposta corresponder à implementação antiga, reiniciar o backend a partir deste workspace e repetir a captura. Se não for possível determinar a versão, preparar logs de etapa e reiniciar o processo para garantir que a instrumentação esteja carregada.

**Saída esperada:** evidência de que frontend e backend ativos usam o mesmo contrato. Não basta repetir `/auth/google/status`.

### 2. Reproduzir uma tentativa com captura completa

- Abrir exatamente `http://localhost:5173/entrar` e anotar o texto integral do erro, onde aparece e o último estado visível do popup.
- Abrir Console e Network na janela principal e no popup, com preservação dos registros durante navegação.
- Anotar horário e modo da tentativa. Acompanhar o identificador aleatório desde `/google/start` até a mensagem recebida pela janela principal.
- Capturar status, redirecionamentos e duração de cada etapa. Se houver erro na tela do Google, registrar o código exibido e priorizar esse erro antes da comunicação do popup.
- Reproduzir popup e mesma aba em tentativas separadas, cada uma com estado OAuth novo. Não reutilizar códigos de autorização nem misturar tentativas simultâneas.
- O fallback hoje só aparece quando a abertura do popup é bloqueada. Para compará-lo, usar esse caminho ou uma entrada temporária de diagnóstico que invoque o modo `redirect` já existente.
- Evitar limpar cookies antes da primeira captura, pois isso pode remover evidências. Se necessário, fazer depois uma segunda rodada com cookies apenas deste aplicativo removidos, registrando essa diferença.

**Saída esperada:** uma sequência única da falha, sem misturar refresh inicial, chamadas de diagnóstico e tentativa de login.

### 3. Instrumentar as etapas que hoje não ficam distinguíveis

Arquivos principais: `backend/app/modules/auth/controller.py`, `frontend/src/pages/AuthPage.jsx` e `frontend/src/pages/GoogleAuthComplete.jsx`.

- No backend, registrar horário, identificador da tentativa quando disponível, etapa, resultado e motivo controlado: início, cookie ausente/inválido, comparação de estado, erro retornado pelo Google, troca do código, validação do token, criação da sessão e preparação do redirecionamento.
- No callback, registrar sucesso apenas depois da criação da sessão. Distinguir cookie ausente de cookie inválido e de estado divergente. Quando não houver identificador recuperável, correlacionar por horário e um identificador interno da requisição.
- No frontend, registrar temporariamente a chegada à conclusão, presença de `window.opener`, origem atual, presença do identificador e envio/recebimento da mensagem. Distinguir rejeição por origem, janela, formato e identificador, sem flexibilizar essas validações.
- Não registrar códigos OAuth, `state`, `nonce`, verificador PKCE, tokens, cookies, segredos, dados pessoais ou URLs de callback completas. Sanitizar capturas antes de anexá-las a arquivos ou compartilhar um HAR.

**Saída esperada:** cada falha recebe uma etapa e um motivo, incluindo as saídas precoces que atualmente terminam apenas em 303.

### 4. Verificar estado OAuth, cookies e origens

- Confirmar origem da janela principal, URL pública de início, callback e página de conclusão. Comparar protocolo, host e porta; verificar especialmente `localhost` versus `127.0.0.1` e 5173 versus 5174.
- Em `/api/auth/google/start`, verificar se `expenses_google_oauth` foi armazenado, com caminho `/api/auth/google`, e se o navegador o envia ao callback.
- Se não for enviado, usar o motivo de bloqueio mostrado pelo navegador para investigar caminho, domínio, protocolo, atributos ou política de cookies.
- Se o cookie chegar, conferir validade, assinatura e igualdade do estado no servidor, sem registrar os valores. Verificar se outra tentativa sobrescreveu o cookie ou se a tentativa excedeu o prazo.

**Saída esperada:** confirmação de estado válido ou explicação verificável para a rejeição antes da troca do código.

### 5. Separar autenticação Google, sessão e comunicação do popup

| Observação na mesma tentativa | Próxima investigação |
| --- | --- |
| O Google mostra um erro antes do callback | Usar o código exibido para conferir cliente, callback e configuração de acesso no Console |
| Callback retorna erro ou não informa `result`/`request_id` conforme o contrato | Priorizar versão do backend e motivo/etapa do callback |
| Callback informa sucesso, mas não há refresh posterior | Conferir carregamento de `/auth/complete`, Console, `window.opener`, `postMessage` e filtros de recebimento |
| `postMessage` é rejeitado | Comparar origens, janela e identificador; corrigir o desencontro preservando as validações |
| Comunicação funciona na mesma aba e falha no popup | Priorizar a comunicação entre janelas e cabeçalhos de isolamento efetivamente recebidos |
| Callback informa sucesso e refresh retorna 401 | Verificar se `expenses_refresh` foi aceito e enviado; depois investigar sessão, expiração, revogação e rotação |
| Refresh retorna 500 | Usar a etapa e a exceção controlada para investigar banco, chaves e criação/serialização da resposta |
| Refresh retorna 200, mas a tela não abre | Conferir `AuthProvider`, troca da rota de conclusão pela aplicação e chamada protegida com access token |

Também verificar duplicação de eventos e chamadas durante desenvolvimento com React StrictMode e durante a troca dos providers. A existência de deduplicação no cliente deve ser comprovada na captura, sem atribuir a ela a falha por antecipação.

### 6. Corrigir a causa comprovada

- Aplicar uma alteração localizada que explique a primeira divergência capturada.
- Se a origem for processo desatualizado, corrigir a inicialização e a identificação da versão em execução, além do reinício necessário.
- Se houver falha no fallback após exceção de `postMessage`, inspecionar seu comportamento real: atualmente o `catch` tem comentário de recuperação, mas não altera `hasOpener`; verificar se a restauração na própria aba realmente é alcançada nesse caso.
- Preservar validações OAuth e de mensagens. Não tentar resolver a falha aceitando qualquer origem, ignorando estado/nonce, expondo tokens em URLs ou desativando a rotação.
- Reproduzir a mesma tentativa depois da correção e comparar a primeira divergência com a captura anterior.

### 7. Validar a correção e registrar a conclusão

- Executar os testes de autenticação existentes e o build após a alteração pertinente. Adicionar uma regressão quando a causa exigir cobertura que ainda não existe; não repetir apenas os testes já aprovados como prova de integração real.
- Conferir em navegador: popup, mesma aba, retorno ao destino pretendido, cancelamento, popup fechado e nova tentativa.
- Confirmar refresh 200, uma chamada protegida bem-sucedida, recarregamento da página, renovação e logout. Verificar ausência de rotação concorrente inesperada na mesma tentativa.
- Registrar causa demonstrada, arquivo ou configuração alterada, evidência anterior e posterior, verificações realizadas e eventuais limitações. Atualizar o estado operacional em `PLANO_LOGIN_GOOGLE.md`.

## Critérios de encerramento

- [ ] A primeira etapa que falhava foi identificada em uma tentativa real.
- [ ] Frontend e backend ativos usam o mesmo contrato de conclusão.
- [ ] Callback bem-sucedido define o cookie e leva à confirmação da sessão.
- [ ] A janela principal recebe o resultado e abre uma rota protegida sem atualização manual.
- [ ] O fallback pela mesma aba também conclui a navegação.
- [ ] A sessão funciona após recarregar; renovação e logout foram verificados.
- [ ] Testes pertinentes e build aprovados após a correção final.
- [x] O usuário confirmou que o sintoma original deixou de ocorrer em 24/10/2026, após o reinício do backend.

O sintoma original foi resolvido operacionalmente e confirmado pelo usuário nesta rodada. A checklist restante registra cenários ainda não acompanhados e limites da investigação; não constitui uma validação completa de todos os fluxos descritos no plano.
