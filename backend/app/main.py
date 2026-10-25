from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import pengaturan
from .db import buka_pool, koneksi, tutup_pool
from .deps import cek_asal
from .galat import Galat
from .routers import analisis, auth, chat, latihan, materi, siswa, soal, terhubung


@asynccontextmanager
async def lifespan(_: FastAPI):
    buka_pool()
    yield
    tutup_pool()


docs = pengaturan().docs_aktif
app = FastAPI(
    title="Bemai API", lifespan=lifespan,
    docs_url="/api/docs" if docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if docs else None,
)

api = APIRouter(prefix="/api", dependencies=[Depends(cek_asal)])
for r in (auth.router, materi.baca, materi.tulis, soal.baca, soal.tulis,
          latihan.router, chat.router, analisis.router, siswa.router, terhubung.router):
    api.include_router(r)


@api.get("/health", tags=["kesehatan"])
def health(conn=Depends(koneksi)):
    conn.execute("select 1")
    return {"status": "ok"}


app.include_router(api)


def _galat(status: int, kode: str, pesan: str) -> JSONResponse:
    return JSONResponse({"error": {"kode": kode, "pesan": pesan}}, status_code=status)


@app.exception_handler(Galat)
async def galat_kita(_: Request, e: Galat):
    return _galat(e.status, e.kode, e.pesan)


@app.exception_handler(StarletteHTTPException)
async def galat_http(_: Request, e: StarletteHTTPException):
    kode = {404: "tidak_ada", 405: "metode_tidak_didukung"}.get(e.status_code, "galat")
    return _galat(e.status_code, kode, str(e.detail))


@app.exception_handler(RequestValidationError)
async def galat_validasi(_: Request, e: RequestValidationError):
    return _galat(400, "data_tidak_valid", "Data yang dikirim tidak valid")


@app.middleware("http")
async def jangan_simpan_cache(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["Cache-Control"] = "no-store"
    return resp
