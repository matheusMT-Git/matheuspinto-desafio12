from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.erros import ErroNegocio
from app.services import agenda as servico_agenda
from app.services import dashboard as servico_dashboard
from app.services import escalas as servico_escalas
from app.services import servidores as servico_servidores
from app.utils import hoje, semana_de
from app.web.templating import templates

router = APIRouter(tags=["web"], include_in_schema=False)

DIAS_DA_SEMANA = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]


def _inteiro(valor: str) -> int | None:
    """Filtros de formulário chegam como texto; vazio ou inválido significa 'todos'."""
    return int(valor) if valor.strip().isdigit() else None


def _data(valor: str, padrao: date) -> date:
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return padrao


@router.get("/", response_class=HTMLResponse)
def pagina_dashboard(
    request: Request,
    inicio: str = "",
    fim: str = "",
    setor_id: str = "",
    db: Session = Depends(get_db),
) -> Response:
    segunda, domingo = semana_de(hoje())
    inicio_d, fim_d, setor = _data(inicio, segunda), _data(fim, domingo), _inteiro(setor_id)
    contexto: dict[str, Any] = {
        "inicio": inicio_d,
        "fim": fim_d,
        "setor_id": setor,
        "setores": servico_escalas.listar_setores(db),
        "dados": None,
        "erro": None,
    }
    try:
        dados = servico_dashboard.calcular_dashboard(db, inicio_d, fim_d, setor)
        contexto["dados"] = dados
        contexto["rotulos"] = [d.data.strftime("%d/%m") for d in dados.serie_por_dia]
        contexto["ocupadas"] = [d.ocupadas for d in dados.serie_por_dia]
        contexto["livres"] = [d.livres for d in dados.serie_por_dia]
    except ErroNegocio as exc:
        contexto["erro"] = exc.mensagem
    return templates.TemplateResponse(
        request, "dashboard.html", contexto, status_code=422 if contexto["erro"] else 200
    )


@router.get("/agenda", response_class=HTMLResponse)
def pagina_agenda(
    request: Request,
    semana: str = "",
    servidor_id: str = "",
    setor_id: str = "",
    db: Session = Depends(get_db),
) -> Response:
    segunda, domingo = semana_de(_data(semana, hoje()))
    servidor, setor = _inteiro(servidor_id), _inteiro(setor_id)
    turnos = servico_agenda.consultar_agenda(db, segunda, domingo, servidor, setor)
    dias = [
        {
            "data": segunda + timedelta(days=i),
            "nome": DIAS_DA_SEMANA[i],
            "turnos": [t for t in turnos if t.data == segunda + timedelta(days=i)],
        }
        for i in range(7)
    ]
    contexto = {
        "dias": dias,
        "segunda": segunda,
        "domingo": domingo,
        "anterior": segunda - timedelta(days=7),
        "proxima": segunda + timedelta(days=7),
        "servidor_id": servidor,
        "setor_id": setor,
        "servidores": servico_servidores.listar_servidores(db),
        "setores": servico_escalas.listar_setores(db),
        "total_turnos": len(turnos),
    }
    return templates.TemplateResponse(request, "agenda.html", contexto)
