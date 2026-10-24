# Expenses

Aplicação pessoal para registrar compras, consultar as compras recentes e acompanhar cobranças mês a mês. A interface usa React, navegação compartilhada com History API, cache de requisições reutilizado entre as rotas e gráficos SVG responsivos. Os dados de despesas são gravados na API e persistem no banco configurado pelo backend.

## Requisitos

- Node.js 20.19+ ou 22.12+
- pnpm
- Backend e PostgreSQL configurados conforme `../backend/README.md`

## Executar localmente

1. Instale as dependências: `pnpm install`.
2. No primeiro uso, cadastre as referências padrão no backend a partir de `backend`: `.venv\Scripts\python.exe -m app.seed`.
3. Ainda em `backend`, inicie a API: `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.
4. Em `frontend`, copie `.env.example` para `.env` se quiser personalizar a configuração: `Copy-Item .env.example .env`.
5. Em `frontend`, inicie o Vite: `pnpm dev`.
6. Abra o endereço informado pelo Vite, normalmente `http://localhost:5173`.

## Configuração do ambiente

As variáveis abaixo são opcionais; os padrões permitem usar a API local sem criar um arquivo `.env`:

| Variável | Padrão | Uso |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Endereço base das requisições feitas pelo navegador. Aceita um caminho na mesma origem ou uma URL absoluta, como `https://api.exemplo.com`. Barras finais são removidas. |
| `BACKEND_PROXY_TARGET` | `http://127.0.0.1:8000` | Endereço do backend para o proxy `/api` do Vite, usado em `pnpm dev` e `pnpm preview`. O proxy remove `/api` antes de encaminhar a requisição. |

Por exemplo, se apenas a porta do backend local mudar, mantenha `VITE_API_BASE_URL=/api` e ajuste `BACKEND_PROXY_TARGET`. Reinicie o Vite após alterar arquivos de ambiente. O proxy só atende requisições iniciadas por `/api`; uma URL absoluta em `VITE_API_BASE_URL` faz o navegador acessar a API diretamente, sem passar por ele.

Em produção, uma opção é manter `VITE_API_BASE_URL=/api` e configurar o servidor ou serviço de hospedagem para encaminhar `/api` ao backend, removendo esse prefixo. Outra opção é informar em `VITE_API_BASE_URL` a URL pública HTTPS do backend na **compilação**; se estiver em outra origem, o backend ou o servidor intermediário precisará permitir CORS para a origem do frontend. O backend atual não configura CORS. O proxy do Vite não é um proxy de produção.

Variáveis `VITE_` são incorporadas ao código entregue ao navegador e são públicas: nunca coloque senhas, tokens ou outras credenciais nelas. Valores em `.env` e `.env.*` são locais e ignorados pelo Git, com exceção dos arquivos `.env.example`. Alterações em `VITE_API_BASE_URL` exigem um novo build para afetar os arquivos publicados.

`/entrar` oferece login somente com Google. `/cadastro` redireciona para o login; o cadastro acontece automaticamente na primeira autenticação Google. O botão abre um popup OAuth; se o navegador bloquear a janela, a própria tela oferece continuar na mesma aba. O access token fica em memória, e o refresh token em cookie `HttpOnly`, então recarregar restaura a sessão sem guardar tokens em armazenamento do navegador. Configure as credenciais OAuth e o callback local conforme `../backend/README.md`. As contas autenticadas compartilham o conjunto atual de despesas e entradas.

As rotas de negócio são `/despesas`, `/gastos` e `/consolidado`. A rota `/gastos` mostra cobranças e reembolsos numa lista única, ordenada por data do evento; os reembolsos aparecem negativos e em vermelho. O resumo traz valores brutos, reembolsos e líquido. É possível filtrar por categoria, meio de pagamento e busca; filtros e página ficam na URL. O filtro por meio de pagamento afeta apenas cobranças. Os filtros do consolidado também ficam na URL e podem ser preservados ao recarregar a página. As referências e os resultados são mantidos em cache local por até 30 minutos e 2 minutos, respectivamente.

Para gerar uma versão de produção, execute `pnpm build`. Os arquivos gerados ficam em `dist/`. A hospedagem deve redirecionar rotas da aplicação, como `/despesas`, `/gastos` e `/consolidado`, para `index.html`.
