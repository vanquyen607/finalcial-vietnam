from __future__ import annotations

from fastapi import Header, HTTPException

from ..config import settings


async def require_token(x_api_token: str | None = Header(default=None)) -> None:
    """Chặn API ghi khi đã cấu hình GOLD_API_TOKEN mà thiếu/sai token.

    Token rỗng (mặc định dev local) = cho qua để không gãy trải nghiệm hiện tại.
    """
    expected = settings.api_token
    if not expected:
        return
    if x_api_token != expected:
        raise HTTPException(401, "Thiếu hoặc sai API token (header X-Api-Token)")
