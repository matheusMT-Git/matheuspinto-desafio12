class ErroNegocio(Exception):
    """Erro de regra de negócio; vira {"detail": mensagem} com o status indicado."""

    status_code = 400

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class ErroConflito(ErroNegocio):
    status_code = 409


class ErroValidacao(ErroNegocio):
    status_code = 422


class NaoEncontrado(ErroNegocio):
    status_code = 404


def mensagem_validacao(erros: list[dict]) -> str:
    """Resume erros de validação do Pydantic em uma mensagem em português."""
    campos: list[str] = []
    for erro in erros:
        loc = [str(p) for p in erro.get("loc", ()) if p not in ("body", "query", "path")]
        campo = ".".join(loc) or "requisição"
        if campo not in campos:
            campos.append(campo)
    return "Preencha corretamente o(s) campo(s): " + ", ".join(campos) + "."
