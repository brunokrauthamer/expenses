# Plano: acesso ao Expenses somente com Google

Implementado em 22/10/2026 na branch `feat/google-only-login`. Este documento registra a alteração e o estado da validação operacional. Substitui as decisões de login por e-mail/senha do plano anterior, `PLANO_AUTENTICACAO.md`.

**Atualização em 24/10/2026, após nova investigação:** o login voltou a funcionar depois de encerrar o backend antigo e iniciar o código atual com acesso à rede. O usuário confirmou: “Agora entrou”. Client ID, Client Secret e callback do `.env` coincidem com o JSON do Google; nenhum `.env` precisou ser alterado. O resultado, as evidências e os limites da conclusão estão em [PLANO_DEBUG_LOGIN_GOOGLE.md](PLANO_DEBUG_LOGIN_GOOGLE.md).

## Estado da entrega

| Parte | Estado |
| --- | --- |
| Tela somente Google, cadastro automático, popup, confirmação da sessão e fallback na mesma aba | Implementado |
| Endpoints de senha removidos e cadastro antigo redirecionado | Implementado |
| Validação de OAuth, vínculo seguro de identidades, tratamento de erros e documentação | Implementados |
| Testes automatizados do backend e build de produção do frontend | Rodada final em 24/10/2026: 51 testes aprovados, incluindo 15 de autenticação, e build aprovado |
| Cliente OAuth e tela de consentimento no Google Cloud Console | Configurados pelo administrador, conforme confirmação em 24/10/2026 |
| Variáveis de OAuth em `backend/.env` | Presentes; formatos das chaves e URLs locais conferidos em 24/10/2026. Valores secretos não foram copiados para este documento |
| Backend carregando a configuração Google | Reiniciado com o código atual; diagnóstico negativo alcançou o Google e registrou a etapa esperada. Login real posterior criou identidade e sessões, confirmado pelo usuário |
| Fluxo OAuth com conta Google real | Login confirmado pelo usuário após reinício do backend em 24/10/2026; identidade Google e novas sessões observadas no banco. Demais cenários de continuidade e fallback não acompanhados nesta rodada |

### Estado operacional em 24/10/2026

**Resultado final desta rodada:** login funcionando após o reinício do backend, confirmado pelo usuário. O processo antigo iniciou antes da última alteração do controller e não tinha recarga automática. A exceção específica das tentativas antigas não foi capturada; o diagnóstico completo e os cenários ainda não acompanhados estão no plano de debug. Os parágrafos abaixo preservam o histórico anterior a essa recuperação.

O administrador informou que concluiu as etapas no Google Cloud Console e no ambiente. A inspeção local confirmou a presença das variáveis necessárias no `backend/.env`, sem exibir ou registrar valores de credenciais. `GOOGLE_REDIRECT_URI` e `AUTH_FRONTEND_URL` correspondem aos endereços locais esperados, e as chaves de autenticação existentes passaram por verificações de formato.

Na primeira verificação documentada, a API retornou `{"enabled":false}` e a tentativa de reiniciar o Uvicorn não conseguiu encerrar o listener da porta 8000. Esse resultado foi superado por verificações posteriores que retornaram `{"enabled":true}` diretamente e pelo proxy. Isso comprova a presença da configuração Google no processo, mas não sua validade nem a versão do código carregada. Os logs mostram callbacks com 303, que no controller atual podem indicar sucesso ou falha tratada; o resultado precisa ser capturado no redirecionamento.

Foram ajustadas a atualização da rota em `Root` e a porta fixa do Vite. As instâncias anteriores do frontend foram encerradas e uma nova instância respondeu na porta 5173. O usuário informou que o login continua falhando depois dessas ações. O próximo passo prioritário é conferir o contrato efetivamente retornado pelo backend e correlacionar uma tentativa real até a confirmação da sessão, conforme o novo plano de debug.

## Resultado esperado

Ao abrir `/entrar`, a pessoa verá a marca Expenses, uma explicação breve e o botão **Continuar com Google**. Ao clicar, escolherá sua conta e se autenticará na janela do próprio Google. O Expenses criará a conta interna automaticamente no primeiro acesso e abrirá o aplicativo; acessos seguintes reutilizarão a mesma identidade.

O Google será a única forma de iniciar uma nova sessão. Serão removidos os campos de e-mail/senha, a confirmação de senha e o cadastro separado. O acesso antigo a `/cadastro` redirecionará para `/entrar`.

Qualquer conta Google válida e com e-mail verificado poderá acessar, incluindo contas Google que não usam Gmail. Será mantida a regra atual de dados compartilhados: as pessoas autenticadas verão e poderão administrar o mesmo conjunto de despesas e entradas. Separar dados por pessoa não faz parte desta tarefa.

## O que já existe e será aproveitado

- `backend/app/modules/auth/controller.py`: início e callback Google, troca do código no servidor, validação do ID token e cookie de refresh.
- `backend/app/modules/auth/service.py`: criação de usuários, identidades externas, sessões e proteção do estado temporário com `state`, `nonce` e PKCE.
- `users`, `external_identities` e `refresh_sessions`: estruturas já criadas pela migração `20261022_0007`.
- `frontend/src/shared/AuthContext.jsx` e `frontend/src/services/api.js`: access token em memória, restauração de sessão, renovação e saída.

Antes da implementação, o botão Google só aparecia quando o backend informava configuração disponível e usava `window.location`, substituindo a página inteira. A rota `/auth/complete` também passava pela restauração automática de sessão do `AuthProvider`; o fluxo foi ajustado para que o popup não dispute o mesmo refresh token com a janela principal.

Há dois ajustes concretos de configuração identificados: `iniciar.ps1` abre `http://127.0.0.1:5173`, enquanto os exemplos de callback e de frontend usam `http://localhost:5173`, e esses hosts têm cookies distintos. O estado OAuth é assinado com o PyJWT já usado pelo projeto, sem adicionar dependências.

## Solução escolhida

Manter o fluxo OpenID Connect com Authorization Code e PKCE já existente e adaptá-lo para popup. Isso permite aproveitar o backend e as sessões atuais sem adicionar Firebase, outro serviço de autenticação ou dependências React para o login.

A aplicação iniciará o fluxo pelo endpoint oficial de autorização do Google. A página `https://accounts.google.com/v3/signin/` mencionada pelo usuário é uma das telas internas que o Google pode apresentar, e não será usada diretamente como endereço de integração. A seleção da tela de autenticação será feita pelo Google. Referência: [OpenID Connect do Google](https://developers.google.com/identity/openid-connect/openid-connect).

O botão utilizará um recurso oficial do Google com o texto em português. O usuário autorizou as cores oficiais **apenas no logotipo do Google**, inclusive o verde; a proibição de verde permanece no restante da interface. Referência: [diretrizes visuais do botão Google](https://developers.google.com/identity/branding-guidelines).

## Etapas de implementação

### 1. Preparar a configuração Google

1. Criar ou reutilizar um projeto no Google Cloud Console e cadastrar um cliente OAuth do tipo aplicação web.
2. Configurar nome do aplicativo, contato, público e os escopos mínimos `openid email profile`. Durante os testes, configurar as contas de teste conforme o modo do projeto; para disponibilizar a qualquer conta, preparar a publicação do aplicativo no Google.
3. Padronizar o endereço local acessado pelo navegador em `http://localhost:5173`, alinhando o inicializador e a documentação. O proxy poderá continuar se conectando ao backend em `127.0.0.1:8000`.
4. Registrar o callback público exato `http://localhost:5173/api/auth/google/callback` e, na implantação, o callback HTTPS do domínio real. O caminho público inclui `/api`; o proxy o remove antes de chegar ao FastAPI. A URL deve coincidir com a cadastrada no Google, conforme a [documentação OAuth](https://developers.google.com/identity/protocols/oauth2/web-server).
5. Configurar `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` e `AUTH_FRONTEND_URL` no ambiente do backend. Validar também as chaves de autenticação existentes e o caminho dos cookies. Em produção, usar HTTPS e `AUTH_COOKIE_SECURE=true`.
6. Assinar e validar o cookie temporário usando o PyJWT já presente no backend, com emissor, audiência e validade de dez minutos.

O segredo do cliente fica somente no backend. Nenhum segredo deve ser pedido no chat, incluído em `VITE_`, documentado com valor real ou enviado ao Git. A configuração do Console e o preenchimento do ambiente local foram informados como concluídos pelo administrador em 24/10/2026; o processo ativo posteriormente retornou `enabled: true`, mas a validade da configuração e o fluxo real ainda precisam ser confirmados. Para produção, também é necessário configurar o domínio de hospedagem e o callback HTTPS correspondente.

### 2. Tornar o Google a única entrada

- Simplificar `AuthPage.jsx` para uma única tela, retirando o formulário e o link de cadastro.
- Remover as chamadas de senha do cliente HTTP e as operações correspondentes do contexto de autenticação.
- Retirar as rotas públicas `POST /auth/login` e `POST /auth/register` do backend. Elas deverão responder 404 após a alteração, inclusive quando chamadas diretamente, sem depender da interface para impedir login por senha.
- Redirecionar `/cadastro` para `/entrar`, preservando um destino interno válido quando houver.
- Preservar contas, identidades e dados existentes. A tabela `local_credentials` poderá permanecer sem uso; não apagar hashes nem alterar migrações já aplicadas. Não há mudança de esquema prevista para esta entrega.
- Manter a validade atual das sessões já emitidas; a troca de método de entrada não fará uma revogação em massa. Novas autenticações ocorrerão somente pelo Google.

### 3. Abrir o popup e concluir a sessão na janela principal

1. No clique do botão, abrir a janela imediatamente, sem aguardar uma chamada assíncrona, e guardar sua referência. Impedir cliques repetidos durante a tentativa.
2. Abrir `/api/auth/google/start` informando o modo de apresentação, um identificador aleatório da tentativa e o destino interno pretendido. O backend validará esses campos e os incluirá no estado protegido do fluxo.
3. O backend redirecionará o popup ao Google. A autenticação e eventual senha serão tratadas exclusivamente nas páginas do Google.
4. O callback validará `state`, PKCE, assinatura, emissor, audiência, expiração, `nonce` e e-mail verificado antes de criar qualquer sessão. Conta interna desativada continuará impedida de entrar.
5. Após criar ou localizar a conta, o backend definirá o refresh cookie e redirecionará o popup para uma página de conclusão do frontend. URLs e mensagens não carregarão tokens nem dados pessoais; apenas resultado e identificador da tentativa.
6. A página de conclusão, fora da restauração automática do `AuthProvider`, notificará a janela principal por `postMessage` com `targetOrigin` explícito. A janela principal validará origem, `event.source`, formato e identificador da tentativa. A mensagem será somente um aviso para consultar a sessão, sem autenticar ninguém por si só.
7. A janela principal chamará uma única vez o refresh já deduplicado pelo cliente HTTP, atualizará usuário e token em memória e abrirá o destino solicitado ou `/despesas`. Somente rotas internas permitidas, incluindo seus filtros, serão aceitas como destino.
8. O popup encerrará sua participação e será fechado quando permitido. Listeners, timers e referências serão limpos ao terminar, cancelar ou desmontar a tela.

O fallback será explícito: se o navegador bloquear a janela, oferecer **Continuar nesta aba**, usando o mesmo fluxo OAuth em modo de redirecionamento. Nesse modo, ou sem janela principal disponível, a página de conclusão restaurará a sessão na própria aba. A configuração de hospedagem deverá permitir a comunicação entre as janelas; os testes verificarão também a política de isolamento de janelas do navegador.

### 4. Definir criação e vínculo das contas

- Usar o identificador estável `sub` do Google para localizar a identidade; o e-mail será dado de perfil.
- Criar usuário e identidade automaticamente na primeira autenticação válida, em transação, preservando a criptografia e os índices HMAC atuais.
- Reutilizar a identidade em acessos seguintes e tratar concorrência para não criar registros duplicados.
- Corrigir o vínculo atual por e-mail: uma coincidência com conta local só poderá gerar associação automática quando o Google for autoridade sobre o endereço, como Gmail ou Workspace com `email_verified=true` e `hd` válido. O e-mail verificado de um provedor externo, sozinho, não comprova propriedade atual. Referência: [validação de identidade Google](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token).
- Na colisão com conta local que não possa ser associada com segurança, não criar duplicata nem vincular silenciosamente. Exibir mensagem orientando regularização assistida; qualquer associação administrativa dependerá de comprovar a titularidade. Isso não restringe o primeiro cadastro de contas Google com e-mail externo sem colisão.
- Descartar os tokens do Google depois de validar a identidade; a sessão de uso do aplicativo continuará sendo a do Expenses.

### 5. Tratar os estados da tela

- Botão principal visível, com estados de carregamento e tentativa em andamento.
- Configuração ausente ou API indisponível: mensagem clara, ação de tentar novamente quando aplicável e botão temporariamente desabilitado; a única opção de login não desaparecerá silenciosamente.
- Popup fechado, acesso cancelado, tentativa expirada, falha do Google ou sessão não confirmada: retornar ao estado pronto e permitir nova tentativa com mensagem em português.
- Limpar o cookie OAuth temporário tanto no sucesso quanto na falha e aplicar tempo limite à tentativa.
- Converter erros conhecidos em mensagens controladas na página de conclusão, evitando deixar o usuário diante de JSON no popup.
- Preservar layout responsivo, foco visível, teclado, contraste, áreas de toque e movimento reduzido.
- Manter access token somente em memória e refresh token em cookie `HttpOnly`, com a política atual de renovação e logout. Sair do Expenses encerrará a sessão do aplicativo.

### 6. Validar e atualizar a documentação

**Backend:** adaptar testes que hoje criam sessões por `/auth/register` para fixtures de usuários/identidades Google e sessões de teste. Cobrir configuração, URL de autorização, PKCE, cookie temporário, callback válido, cancelamento, estado ausente/adulterado/expirado, `nonce` inválido, tokens inválidos e falhas de rede. Simular troca de código e chaves Google nos testes automatizados, sem depender de contas reais ou alterar o PostgreSQL local.

Cobrir também primeiro acesso, usuário recorrente, colisões de identidade, conta desativada, impossibilidade de login/cadastro por senha, refresh, logout e proteção das rotas de negócio. Conferir que o refresh token não aparece em JSON nem em mensagens entre janelas e que o cookie OAuth é removido nos dois resultados.

**Frontend:** verificar no navegador o popup, autenticação confirmada pela API, retorno ao destino original com filtros, fechamento/cancelamento, bloqueio com fallback, configuração ausente, falha de API, tentativas repetidas, rejeição de mensagens de outra origem/janela e ausência de corrida de refresh entre popup e janela principal. Repetir os fluxos essenciais em celular, teclado e com movimento reduzido.

Executar a suíte disponível do backend e o build do frontend; corrigir falhas da alteração. Fazer uma validação real com Google depois que as credenciais e o callback estiverem configurados. Atualizar `CONTEXTO.md`, os READMEs, os exemplos de ambiente e o plano anterior para refletirem o comportamento efetivamente entregue.

## Arquivos principais previstos

| Área | Arquivos |
| --- | --- |
| Tela e conclusão | `frontend/src/pages/AuthPage.jsx`, nova página de conclusão, `frontend/src/main.jsx`, `frontend/src/styles.css` e ajustes de viewport se necessários |
| Estado e cliente HTTP | `frontend/src/shared/AuthContext.jsx`, `frontend/src/services/api.js` e módulo reutilizável para coordenação do popup |
| Autenticação no servidor | `backend/app/modules/auth/controller.py`, `service.py`, `schema.py` e dependências/configuração do módulo |
| Instalação e início local | `backend/requirements.txt`, `backend/.env.example`, `iniciar.ps1` |
| Validação e documentação | `backend/tests/test_auth.py`, `backend/tests/conftest.py`, READMEs, `CONTEXTO.md`, `PLANO_AUTENTICACAO.md` |

Implementação entregue na branch `feat/google-only-login`, sem commit, PR ou publicação nesta etapa.

## Critérios de aceite

1. `/entrar` apresenta somente a opção Google para iniciar uma sessão; `/cadastro` leva ao login e os antigos endpoints de senha não funcionam.
2. O clique abre a autenticação oficial Google em popup; a primeira entrada cria a conta e as seguintes reutilizam a identidade.
3. A janela principal confirma a sessão no backend antes de abrir a rota privada, sem atualização manual e sem transportar tokens entre janelas.
4. Recarregar a página restaura a sessão; expiração e saída continuam funcionando.
5. Cancelamentos, falhas, popup bloqueado e configuração ausente têm tratamento claro e permitem recuperação.
6. URLs locais, callbacks, cookies e proxy estão alinhados, e o fluxo real foi validado com credenciais Google.
7. Os dados financeiros existentes e a regra de compartilhamento foram preservados; os testes disponíveis e o build passam.
