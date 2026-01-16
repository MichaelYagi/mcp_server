# client/a2a_client.py
from typing import Any, Dict, List
import uuid
import httpx

class A2AClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def _rpc(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/a2a", json=payload)
            resp.raise_for_status()
            data = resp.json()

        if "error" in data:
            raise RuntimeError(f"A2A error: {data['error']}")
        return data.get("result", {})

    async def discover(self) -> Dict[str, Any]:
        return await self._rpc("a2a.discover", {})

    async def call(self, tool: str, arguments: Dict[str, Any]) -> Any:
        return await self._rpc("a2a.call", {
            "tool": tool,
            "arguments": arguments,
        })
