# Plano de autenticação

Atualizado em 22/10/2026. A primeira versão foi implementada no código e a migração `20261022_0007` foi aplicada ao PostgreSQL local. Configure as chaves descritas em `backend/README.md` antes de cadastrar a primeira conta; outras instalações também precisam aplicar essa migração.

## Objetivo e escopo inicial

- Exigir que toda chamada à API de negócio seja feita por uma pessoa autenticada.
- Permitir criação de conta por e-mail e senha ou entrada com uma conta Google.
- Oferecer uma tela de login e uma tela de cadastro responsivas, acessíveis e em português brasileiro.
- Manter despesas, entradas, categorias e meios de pagamento **compartilhados**: qualquer pessoa autenticada pode listar, criar, editar e excluir qualquer registro. Não será criado `user_id` nas tabelas de negócio nesta fase.
- Proteger dados de usuário em repouso. Senhas, por definição, não serão reversivelmente criptografadas: serão armazenadas apenas como hashes Argon2id, que é a proteção correta para senhas.

Não fazem parte desta entrega: recuperação de senha, confirmação de e-mail, perfis/roles, exclusão de conta, auditoria detalhada e isolamento dos gastos por usuário. Eles devem ser incluídos antes de uma abertura pública do produto, especialmente os dois primeiros fluxos que dependem de um provedor de e-mail.

## Arquitetura proposta

O backend continuará sendo um monólito FastAPI. Será criado o módulo `app/modules/auth/`, com `model.py`, `schema.py`, `service.py`, `controller.py` e componentes compartilhados para criptografia e validação de tokens. O módulo será registrado em `app/modules/registry.py` e o roteador em `app/main.py`.

| Área | Decisão |
| --- | --- |
| Contas | Uma conta interna por pessoa, identificada por UUID aleatório e sem significado de negócio. |
| Credenciais locais | E-mail normalizado, senha com hash Argon2id e parâmetros seguros. Nunca guardar senha, confirmação de senha ou senha do Google. |
| Google | OAuth 2.0 / OpenID Connect com fluxo Authorization Code, `state`, `nonce` e PKCE. O backend troca o código e valida emissor, público, assinatura, expiração e `nonce` do ID token. |
| API | Access token JWT assinado assimetricamente (EdDSA ou RS256), enviado em `Authorization: Bearer <token>`. |
| Sessão | Refresh token opaco, rotativo e de uso único, guardado pelo navegador somente em cookie `HttpOnly`, `Secure` e `SameSite=Lax`; o access token fica somente em memória. |
| Autorização inicial | `get_current_user` valida o token para todas as rotas de negócio, mas não filtra dados por usuário. |

O uso de um refresh token opaco evita expor ao cliente dados da sessão e permite revogação imediata. O JWT de acesso curta duração torna a exposição acidental menos impactante. Não usar `localStorage` ou `sessionStorage` para tokens.

## Dados e criptografia em repouso

Criptografia não deve ser delegada à senha do usuário nem a uma única chave gravada no banco. O backend aplicará AES-256-GCM antes de persistir dados pessoais e guardará a chave mestra fora do PostgreSQL: em desenvolvimento, variável de ambiente local não versionada; em produção, um cofre/KMS. A chave terá identificador/versão para permitir rotação. Cada valor recebe nonce aleatório próprio e autenticação de integridade.

Para consultar dados criptografados sem revelar o valor, haverá índices cegos: HMAC-SHA-256 do valor normalizado, com uma chave de índice separada. O índice cego permite localizar e garantir unicidade de e-mail ou identidade Google, mas não substitui a criptografia nem deve ser devolvido pela API.

Tabelas previstas:

| Tabela | Conteúdo | Proteção |
| --- | --- | --- |
| `users` | `id` UUID, e-mail cifrado, índice cego de e-mail, nome cifrado opcional, situação, datas e versão da chave | Campos pessoais cifrados por AES-GCM; índice cego único para o e-mail. |
| `local_credentials` | `user_id`, hash Argon2id da senha, datas de criação/alteração | Hash de senha, nunca cifra reversível. |
| `external_identities` | `user_id`, provedor `google`, assunto (`sub`) cifrado e seu índice cego, datas | O `sub` é cifrado; a combinação provedor/índice cego é única. |
| `refresh_sessions` | `id`, `user_id`, hash/HMAC do refresh token, expiração, revogação, rotação e metadados mínimos | Guardar somente o hash/HMAC do token; não registrar token nem dados pessoais em texto claro. |

O `id` técnico, o estado e datas permanecem em claro porque não carregam conteúdo pessoal e são necessários a chaves estrangeiras, expiração e revogação. Logs, exceções, traces e respostas não devem registrar e-mail, senha, códigos OAuth, tokens, cabeçalhos `Authorization` ou valores cifrados. O banco deve usar TLS em conexões remotas, backup criptografado e acesso mínimo por conta de serviço.

## Contrato HTTP e tokens

Rotas públicas sob `/auth`:

| Rota | Método | Finalidade |
| --- | --- | --- |
| `/auth/register` | `POST` | Cria uma conta de e-mail/senha e inicia uma sessão. |
| `/auth/login` | `POST` | Valida e-mail/senha e inicia uma sessão. |
| `/auth/google/start` | `GET` | Cria estado temporário seguro e redireciona ao Google. |
| `/auth/google/callback` | `GET` | Valida a resposta Google, vincula/cria conta e retorna ao frontend. |
| `/auth/refresh` | `POST` | Consome o refresh cookie, o rotaciona e devolve novo access token. |
| `/auth/logout` | `POST` | Revoga a sessão atual e remove o cookie. |
| `/auth/me` | `GET` | Devolve somente o perfil mínimo da sessão autenticada. |

`register`, `login`, `refresh` e o retorno final do Google respondem com `{ "access_token", "token_type": "bearer", "expires_in", "user" }`. O refresh token nunca aparece no JSON. Ao vencer o access token, o frontend chama `/auth/refresh` uma vez e repete a chamada original; se falhar com 401, limpa o estado e leva a pessoa para `/entrar`.

Access tokens terão expiração de 15 minutos e incluirão, no mínimo, `iss`, `aud`, `sub` (UUID do usuário), `iat`, `exp` e `jti`. A dependência `get_current_user` aceitará apenas o esquema `Bearer`, verificará algoritmo explicitamente permitido, assinatura, emissor, audiência e expiração, e responderá 401 com `WWW-Authenticate: Bearer` para token ausente, inválido ou expirado. Refresh tokens expiram em 30 dias, são rotacionados a cada uso e a reutilização de um token já consumido revoga a família de sessões correspondente.

Após implementar a dependência, ela deve ser aplicada a todas as rotas existentes de `categories`, `expenses`, `income-entries`, `income-categories` e `payment-methods`. As únicas rotas públicas serão as de autenticação, `GET /health` se vier a existir, e a documentação apenas no ambiente de desenvolvimento.

## Fluxos de identidade

### E-mail e senha

1. A pessoa abre `/entrar`, escolhe criar conta e informa e-mail, senha e confirmação.
2. O frontend valida apenas ergonomia; o backend normaliza o e-mail, aplica regras de senha, procura o índice cego e cria os registros em uma transação.
3. O backend calcula Argon2id, cifra os campos pessoais, cria a sessão e responde com o access token; o navegador recebe o refresh token pelo cookie seguro.
4. No login, a resposta para e-mail inexistente e senha incorreta deve ser idêntica, evitando enumeração de contas. Aplicar limitação de tentativas por IP e por índice cego de e-mail.

### Google

1. O botão "Continuar com Google" navega para `/auth/google/start`.
2. O backend cria e armazena temporariamente `state`, `nonce` e o verificador PKCE em cookie seguro de curta duração, depois redireciona ao endpoint de autorização Google.
3. No callback, o backend compara `state`, troca o `code` por tokens no servidor e valida o ID token com as chaves públicas do Google. Não confiar em e-mail ou perfil recebido diretamente pelo frontend.
4. O backend procura a identidade pelo `sub` do Google. Caso não exista, vincula-a a uma conta existente com o mesmo e-mail apenas se o Google tiver informado `email_verified=true`; caso contrário cria uma nova conta. O `sub` é a chave de identidade, não o e-mail.
5. Tokens do Google são descartados após a autenticação: não há necessidade de armazenar access/refresh token do Google para este produto.

As credenciais necessárias são `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e a lista explícita de URLs de callback autorizadas. Elas ficam somente no ambiente seguro e nunca usam o prefixo `VITE_`.

## Tela e comportamento do frontend

Criar `LoginPage.jsx` e `RegisterPage.jsx`, com rotas `/entrar` e `/cadastro`. Ambas terão marca visual consistente com o aplicativo, rótulos associados, mensagens de erro acionáveis, foco visível, navegação por teclado e funcionamento adequado no celular. A página de login inclui e-mail, senha, ação principal "Entrar", link para cadastro e botão "Continuar com Google". A página de cadastro tem os campos necessários e direciona de volta ao login quando a conta já existir.

Será criado um `AuthProvider`/hook central para manter o access token e o usuário em memória, iniciar a sessão por `/auth/refresh` ao carregar a aplicação e expor `login`, `logout` e `authenticated`. O cliente em `frontend/src/services/api.js` acrescentará `Authorization: Bearer ...` a cada chamada protegida, tentará refresh uma única vez diante de 401 e nunca anexará esse cabeçalho às rotas públicas de autenticação.

O roteador protegerá `/despesas`, `/gastos` e `/consolidado`: enquanto a sessão inicial é verificada, mostra estado de carregamento; sem sessão, redireciona para `/entrar` preservando o caminho pretendido; com sessão, um acesso a `/entrar` redireciona para `/despesas`. O cabeçalho substituirá a nota estática por nome/e-mail mínimo e "Sair". Isso controla a experiência, mas a proteção real continua no backend.

## Estado da implementação

1. Concluído: variáveis de ambiente, criptografia AES-GCM com versão, índice HMAC, modelos/migração e dependências.
2. Concluído: cadastro, login, JWT RS256, refresh rotativo, logout e dependência `get_current_user`.
3. Concluído no código: Google OIDC com callback, `state`, `nonce`, PKCE e validação de identidade. Credenciais e URL precisam ser configuradas no Google Cloud Console para ativar o fluxo.
4. Concluído: todos os roteadores de negócio exigem autenticação e mantêm os dados compartilhados, sem `user_id` nas tabelas existentes.
5. Concluído: telas, estado em memória, renovação após 401 e guarda de rotas React.
6. Configuração operacional pendente: em produção, o proxy deve limitar tentativas de login, servir HTTPS e encaminhar `/api` pela mesma origem. Se frontend e API ficarem em origens distintas, configurar CORS restrito com credenciais.
7. Pendente de operação: configurar segredos e OAuth, aplicar a migração ao banco de destino e validar backup antes de publicar.

## Critérios de aceite e testes

- Cadastro cria conta com senha não recuperável em texto claro; o banco não contém e-mail, nome, `sub` Google, token ou senha em claro.
- Login local correto retorna access token Bearer e cookie de refresh; credenciais inválidas retornam a mesma mensagem/estado.
- Um JWT ausente, vencido, com assinatura/audiência/emissor inválidos, ou algoritmo inesperado recebe 401; uma rota de negócio válida recebe `current_user`.
- Refresh funciona uma vez, rotaciona o token e logout/reuso revogam a sessão conforme a política.
- Callback Google inválido (estado, nonce, audiência, emissor ou `email_verified`) é recusado; usuário Google recorrente entra na mesma conta.
- Usuários distintos autenticados conseguem ver e administrar o mesmo gasto registrado, comprovando a regra de dados compartilhados atual.
- O frontend não persiste tokens em Web Storage, recupera sessão após recarregar com refresh cookie, bloqueia rotas privadas e encerra sessão em 401 definitivo.
- A suíte existente continua verde; novos testes cobrem serviços de autenticação, dependência FastAPI, migração e fluxos de interface. Um teste de inspeção de logs garante que segredos não sejam registrados.

## Evolução posterior

Quando houver necessidade de privacidade por pessoa, criar `owner_user_id` opcional nas tabelas de negócio, preencher/decidir a política para os dados já compartilhados e só então filtrar consultas e autorizar escrita pelo proprietário. A simples inclusão da coluna antes dessa decisão não entrega isolamento e pode induzir uma falsa sensação de privacidade.
