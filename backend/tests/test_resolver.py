from unittest.mock import AsyncMock

import pytest

from app.services.icons import ImageResolver


class TestActionsFallback:
    @pytest.mark.anyio
    async def test_action_owner_avatar_fallback(self):
        resolver = ImageResolver(github_token=None)
        resolver.db_cache.resolve = AsyncMock(return_value=None)
        resolver.github.resolve = AsyncMock(return_value=None)
        avatar = ("data:image/png;base64,AAA", "github_org_avatar", "https://github.com/foundry-rs.png")
        resolver.github.resolve_avatar = AsyncMock(return_value=avatar)
        try:
            res = await resolver.resolve_package(
                "foundry-rs/foundry-toolchain@v1", "actions", "foundry-rs/foundry-toolchain"
            )
        finally:
            await resolver.aclose()

        assert res == avatar
        resolver.github.resolve.assert_awaited_once_with(
            "foundry-rs", "foundry-toolchain", "foundry-rs/foundry-toolchain@v1"
        )
        resolver.github.resolve_avatar.assert_awaited_once_with(
            "foundry-rs", "foundry-rs/foundry-toolchain@v1"
        )
