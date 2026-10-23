from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_v1
from app.erros import ErroNegocio, mensagem_validacao
from app.web import escalas as web_escalas

PASTA_STATIC = Path(__file__).parent / "static"

app = FastAPI(title="Escalas de Atendimento")


@app.exception_handler(ErroNegocio)
async def tratar_erro_negocio(_: Request, erro: ErroNegocio) -> JSONResponse:
    return JSONResponse(status_code=erro.status_code, content={"detail": erro.mensagem})


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(_: Request, erro: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422, content={"detail": mensagem_validacao(list(erro.errors()))}
    )


app.mount("/static", StaticFiles(directory=PASTA_STATIC), name="static")
app.include_router(api_v1)
app.include_router(web_escalas.router)


@app.get("/", include_in_schema=False)
def inicio() -> RedirectResponse:
    # O dashboard entra na Sprint 3; até lá a tela inicial é a lista de escalas.
    return RedirectResponse("/escalas")
