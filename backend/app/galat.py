class Galat(Exception):
    """Galat API dengan bentuk seragam: {"error": {"kode": ..., "pesan": ...}} (docs/api.md)."""

    def __init__(self, status: int, kode: str, pesan: str):
        self.status, self.kode, self.pesan = status, kode, pesan
