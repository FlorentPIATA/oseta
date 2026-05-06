"""Tests d'intégration — /sectors (routes/sectors.py)."""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Sector


async def _seed_sector(
    session: AsyncSession,
    code: str = "TECH",
    name: str = "Technology",
    level: str = "macro",
) -> int:
    sector = Sector(code=code, name=name, level=level)
    session.add(sector)
    await session.flush()
    return sector.id  # type: ignore[return-value]


class TestListSectors:
    async def test_empty_returns_empty_list(self, client: AsyncClient) -> None:
        resp = await client.get("/sectors")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_returns_seeded_sectors(self, client: AsyncClient, session: AsyncSession) -> None:
        await _seed_sector(session)
        await session.commit()

        resp = await client.get("/sectors")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["code"] == "TECH"

    async def test_filter_by_level_macro(self, client: AsyncClient, session: AsyncSession) -> None:
        await _seed_sector(session, code="TECH", name="Technology", level="macro")
        await _seed_sector(session, code="SEMI", name="Semiconductors", level="meso")
        await session.commit()

        resp = await client.get("/sectors?level=macro")
        assert len(resp.json()) == 1
        assert resp.json()[0]["code"] == "TECH"

    async def test_filter_by_level_meso(self, client: AsyncClient, session: AsyncSession) -> None:
        await _seed_sector(session, code="TECH", name="Technology", level="macro")
        await _seed_sector(session, code="SEMI", name="Semiconductors", level="meso")
        await session.commit()

        resp = await client.get("/sectors?level=meso")
        assert len(resp.json()) == 1
        assert resp.json()[0]["code"] == "SEMI"


class TestCreateSector:
    async def test_forbidden_without_key(self, client: AsyncClient) -> None:
        resp = await client.post("/sectors", json={"code": "EN", "name": "Energy", "level": "macro"})
        assert resp.status_code == 403

    async def test_forbidden_with_wrong_key(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/sectors",
            json={"code": "EN", "name": "Energy", "level": "macro"},
            headers={"X-Master-Key": "wrong-key"},
        )
        assert resp.status_code == 403

    async def test_create_success_returns_201(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/sectors",
            json={"code": "EN", "name": "Energy", "level": "macro"},
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["code"] == "EN"
        assert data["name"] == "Energy"
        assert data["id"] is not None

    async def test_duplicate_code_returns_409(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        await _seed_sector(session, code="TECH")
        await session.commit()

        resp = await client.post(
            "/sectors",
            json={"code": "TECH", "name": "Technology Duplicate", "level": "macro"},
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 409

    async def test_create_with_parent_id(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        parent_id = await _seed_sector(session, code="TECH", level="macro")
        await session.commit()

        resp = await client.post(
            "/sectors",
            json={"code": "SEMI", "name": "Semiconductors", "level": "meso", "parent_id": parent_id},
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 201


class TestGetSector:
    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/sectors/99999")
        assert resp.status_code == 404

    async def test_found_returns_sector(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session, code="TECH", name="Technology")
        await session.commit()

        resp = await client.get(f"/sectors/{sector_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == sector_id
        assert resp.json()["code"] == "TECH"


class TestSectorCorrelations:
    async def test_sector_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.get("/sectors/99999/correlations")
        assert resp.status_code == 404

    async def test_no_matrix_returns_empty_list(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        sector_id = await _seed_sector(session)
        await session.commit()

        resp = await client.get(f"/sectors/{sector_id}/correlations")
        assert resp.status_code == 200
        assert resp.json() == []
