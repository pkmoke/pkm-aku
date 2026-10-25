"""Local integrated frontend/API entrypoint. No CORS or second proxy required."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from .main import app

class Frontend(StaticFiles):
    async def get_response(self,path,scope):
        if path == 'src/js/data-contoh.js':
            raise HTTPException(404)
        response=await super().get_response(path,scope)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

app.mount('/',Frontend(directory=Path(__file__).resolve().parents[2]/'frontend',html=True),name='frontend')
