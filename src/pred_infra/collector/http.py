from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get_json(base_url: str, params: dict[str, Any] | None = None, timeout: int = 15) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{base_url}{query}"
    request = Request(url, headers={"User-Agent": "pred-infra/0.1"})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)
