export function getQueryErrorMessage(error) {
  if (!error) return 'Não foi possível carregar os dados.';
  if (error.status === 404)
    return 'O endereço da API não foi encontrado. Verifique se o backend está em execução.';
  if (error.status >= 500)
    return 'A API encontrou um problema. Tente novamente em alguns instantes.';
  return error.message || 'Não foi possível carregar os dados.';
}
