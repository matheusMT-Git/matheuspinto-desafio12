// Mostra as mensagens de erro de regra de negócio (409/422) devolvidas pelo servidor.
document.body.addEventListener("htmx:beforeSwap", (evento) => {
  const status = evento.detail.xhr.status;
  if (status === 409 || status === 422 || status === 404) {
    evento.detail.shouldSwap = true;
    evento.detail.isError = false;
  }
});
