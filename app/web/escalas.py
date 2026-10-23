from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.erros import ErroNegocio, ErroValidacao, mensagem_validacao
from app.schemas.escala import EscalaCreate
from app.schemas.turno import TurnoCreate
from app.services import escalas as servico
from app.web.templating import templates

router = APIRouter(tags=["web"], include_in_schema=False)


def _erro(request: Request, erro: ErroNegocio) -> Response:
    return templates.TemplateResponse(
        request, "partials/erro.html", {"mensagem": erro.mensagem}, status_code=erro.status_code
    )


def _texto(form: Any, campo: str) -> str:
    return str(form.get(campo) or "").strip()


def _turnos_do_form(form: Any) -> list[TurnoCreate]:
    """Lê as linhas de turno do formulário; linhas totalmente em branco são ignoradas."""
    colunas = [form.getlist(f"turno_{c}") for c in ("data", "inicio", "fim", "tipo", "vagas")]
    turnos: list[TurnoCreate] = []
    for data, inicio, fim, tipo, vagas in zip(*colunas, strict=False):
        if not (str(data).strip() or str(inicio).strip() or str(fim).strip()):
            continue
        turnos.append(
            TurnoCreate.model_validate(
                {
                    "data": data,
                    "hora_inicio": inicio,
                    "hora_fim": fim,
                    "tipo": tipo,
                    "vagas": vagas,
                }
            )
        )
    return turnos


def _contexto_lista(db: Session, oob: bool = False) -> dict[str, Any]:
    return {"escalas": servico.listar_escalas(db), "oob": oob}


@router.get("/escalas", response_class=HTMLResponse)
def pagina_escalas(request: Request, db: Session = Depends(get_db)) -> Response:
    contexto = {**_contexto_lista(db), "setores": servico.listar_setores(db), "hoje": date.today()}
    return templates.TemplateResponse(request, "escalas/lista.html", contexto)


@router.get("/escalas/turno-linha", response_class=HTMLResponse)
def linha_de_turno(request: Request) -> Response:
    return templates.TemplateResponse(request, "partials/turno_linha.html", {})


@router.post("/escalas", response_class=HTMLResponse)
async def cadastrar_escala(request: Request, db: Session = Depends(get_db)) -> Response:
    form = await request.form()
    try:
        dados = EscalaCreate.model_validate(
            {
                "nome": _texto(form, "nome"),
                "setor_id": _texto(form, "setor_id"),
                "data_inicio": _texto(form, "data_inicio"),
                "data_fim": _texto(form, "data_fim"),
                "turnos": _turnos_do_form(form),
            }
        )
        escala = servico.criar_escala(db, dados)
    except ValidationError as exc:
        return _erro(request, ErroValidacao(mensagem_validacao(list(exc.errors()))))
    except ErroNegocio as exc:
        return _erro(request, exc)
    contexto = {**_contexto_lista(db, oob=True), "escala": escala}
    return templates.TemplateResponse(request, "partials/escala_criada.html", contexto)


@router.get("/escalas/{escala_id}", response_class=HTMLResponse)
def pagina_escala(escala_id: int, request: Request, db: Session = Depends(get_db)) -> Response:
    try:
        escala = servico.obter_escala(db, escala_id)
    except ErroNegocio as exc:
        return _erro(request, exc)
    return templates.TemplateResponse(request, "escalas/detalhe.html", {"escala": escala})


@router.post("/escalas/{escala_id}/turnos", response_class=HTMLResponse)
async def incluir_turno(
    escala_id: int, request: Request, db: Session = Depends(get_db)
) -> Response:
    form = await request.form()
    try:
        dados = TurnoCreate.model_validate(
            {
                "data": _texto(form, "data"),
                "hora_inicio": _texto(form, "hora_inicio"),
                "hora_fim": _texto(form, "hora_fim"),
                "tipo": _texto(form, "tipo"),
                "vagas": _texto(form, "vagas"),
            }
        )
        servico.criar_turno(db, escala_id, dados)
        escala = servico.obter_escala(db, escala_id)
    except ValidationError as exc:
        return _erro(request, ErroValidacao(mensagem_validacao(list(exc.errors()))))
    except ErroNegocio as exc:
        return _erro(request, exc)
    return templates.TemplateResponse(request, "partials/turno_incluido.html", {"escala": escala})


@router.post("/escalas/{escala_id}/publicar", response_class=HTMLResponse)
def publicar_escala(escala_id: int, request: Request, db: Session = Depends(get_db)) -> Response:
    try:
        servico.alterar_status(db, escala_id, "publicada")
    except ErroNegocio as exc:
        return _erro(request, exc)
    return Response(status_code=200, headers={"HX-Redirect": f"/escalas/{escala_id}"})
