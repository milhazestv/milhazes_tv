"""Cliente HTTP minimo.

Stdlib de proposito: menos dependencias significa menos superficie de
supply chain num repositorio que corre sozinho em CI.

O User-Agent identifica o projecto e nao a pessoa. Nao envia cookies,
nao envia referer, nao guarda estado entre corridas.
"""

from __future__ import annotations

import time
import urllib.error
import urllib.request

USER_AGENT = "milhazes-tv/1.0 (observatorio de tempo de emissao; dados publicos)"
TIMEOUT = 30
RETRIES = 3
BACKOFF = 2.0
# Um feed legitimo destes anda pelos 2 MB. O limite existe para que uma
# resposta anomala nao consuma a memoria da maquina da CI.
MAX_BYTES = 32 * 1024 * 1024


class FetchError(RuntimeError):
    pass


def get_text(url: str) -> str:
    last: Exception | None = None
    for attempt in range(RETRIES):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                payload = response.read(MAX_BYTES + 1)
                if len(payload) > MAX_BYTES:
                    raise FetchError(f"resposta demasiado grande de {url}")
                return payload.decode(charset, errors="replace")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if attempt < RETRIES - 1:
                time.sleep(BACKOFF * (attempt + 1))
    raise FetchError(f"falhou o pedido a {url}: {last}")
