from pydantic_settings import BaseSettings, SettingsConfigDict


class Pengaturan(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    asal_diizinkan: str = "http://127.0.0.1:8081"
    cookie_secure: bool = True
    cookie_nama: str = "bemai_sesi"
    sesi_jam: int = 8
    maks_gagal_login: int = 5
    kunci_menit: int = 15
    docs_aktif: bool = False  # Swagger di /api/docs; nyalakan hanya saat pengembangan

    @property
    def asal(self) -> set[str]:
        return {a.strip().rstrip("/") for a in self.asal_diizinkan.split(",") if a.strip()}


_cache: Pengaturan | None = None


def pengaturan() -> Pengaturan:
    global _cache
    if _cache is None:
        _cache = Pengaturan()
    return _cache
