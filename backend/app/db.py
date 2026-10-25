from collections.abc import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import pengaturan

_pool: ConnectionPool | None = None


def buka_pool() -> None:
    global _pool
    if _pool is None:
        # prepare_threshold=None: aman untuk pooler Supabase mode transaksi (tanpa prepared statement)
        _pool = ConnectionPool(
            pengaturan().database_url,
            min_size=1, max_size=10, open=True,
            kwargs={"row_factory": dict_row, "prepare_threshold": None},
        )


def tutup_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def koneksi() -> Iterator[psycopg.Connection]:
    """Dependency FastAPI: satu koneksi per request, commit bila sukses, rollback bila galat."""
    assert _pool is not None, "pool belum dibuka"
    with _pool.connection() as conn:
        yield conn
