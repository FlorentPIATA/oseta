"""Tests d'intégration — /predictions (routes/predictions.py)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Prediction, Sector


async def _seed_sector(session: AsyncSession, code: str = "TECH") -> int:
    s = Sector(code=code, name="Technology", level="macro")
    session.add(s)
    await session.flush()
    return s.id  # type: ignore[return-value]


async def _seed_prediction(session: AsyncSession, sector_id: int, status: str = "pending") -> int:
    pred = Prediction(
        sector_id=sector_id,
        prediction_type="impact_propagation",
        horizon_days=90,
        confidence_score=0.75,
        predicted_direction="positive",
        predicted_magnitude="moderate",
        status=status,
    )
    session.add(pred)
    await session.flush()
    return pred.id  # type: ignore[return-value]


class TestListPredictions:
    async def test_empty_returns_empty_list(self, client: AsyncClient) -> None:
        resp = await client.get("/predictions")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_filter_by_status(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        await _seed_prediction(session, sector_id, status="pending")
        await _seed_prediction(session, sector_id, status="realized")
        await session.commit()

        assert len((await client.get("/predictions?status=pending")).json()) == 1
        assert len((await client.get("/predictions?status=realized")).json()) == 1

    async def test_filter_by_sector_id(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_a = await _seed_sector(session, code="TECH")
        sector_b = await _seed_sector(session, code="ENRG")
        await _seed_prediction(session, sector_a)
        await _seed_prediction(session, sector_b)
        await session.commit()

        resp = await client.get(f"/predictions?sector_id={sector_a}")
        assert len(resp.json()) == 1
        assert resp.json()[0]["sector_id"] == sector_a


class TestTrackRecord:
    async def test_empty_db_returns_null_accuracy(self, client: AsyncClient) -> None:
        data = (await client.get("/predictions/track-record")).json()
        assert data["total"] == 0
        assert data["accuracy"] is None

    async def test_mixed_outcomes_accuracy(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        await _seed_prediction(session, sector_id, status="realized")
        await _seed_prediction(session, sector_id, status="realized")
        await _seed_prediction(session, sector_id, status="failed")
        await session.commit()

        data = (await client.get("/predictions/track-record")).json()
        assert data["total"] == 3
        assert data["realized"] == 2
        assert data["failed"] == 1
        assert data["accuracy"] == pytest.approx(2 / 3, abs=0.01)

    async def test_pending_excluded_from_accuracy_denominator(
        self, client: AsyncClient, session: AsyncSession
    ) -> None:
        sector_id = await _seed_sector(session)
        await _seed_prediction(session, sector_id, status="realized")
        await _seed_prediction(session, sector_id, status="pending")
        await session.commit()

        data = (await client.get("/predictions/track-record")).json()
        assert data["pending"] == 1
        assert data["accuracy"] == pytest.approx(1.0)  # 1 realized / 1 settled


class TestGetPrediction:
    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        assert (await client.get("/predictions/99999")).status_code == 404

    async def test_found_returns_prediction(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        pred_id = await _seed_prediction(session, sector_id)
        await session.commit()

        resp = await client.get(f"/predictions/{pred_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == pred_id
        assert resp.json()["status"] == "pending"


class TestRealizePrediction:
    async def test_forbidden_without_key(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        pred_id = await _seed_prediction(session, sector_id)
        await session.commit()

        assert (await client.patch(f"/predictions/{pred_id}/realize?outcome=realized")).status_code == 403

    async def test_realize_success(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        pred_id = await _seed_prediction(session, sector_id)
        await session.commit()

        resp = await client.patch(
            f"/predictions/{pred_id}/realize?outcome=realized",
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "realized"
        assert resp.json()["realized_at"] is not None

    async def test_cannot_realize_already_settled(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        pred_id = await _seed_prediction(session, sector_id, status="realized")
        await session.commit()

        resp = await client.patch(
            f"/predictions/{pred_id}/realize?outcome=failed",
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 409

    async def test_cannot_set_outcome_to_pending(self, client: AsyncClient, session: AsyncSession) -> None:
        sector_id = await _seed_sector(session)
        pred_id = await _seed_prediction(session, sector_id)
        await session.commit()

        resp = await client.patch(
            f"/predictions/{pred_id}/realize?outcome=pending",
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 400

    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        resp = await client.patch(
            "/predictions/99999/realize?outcome=realized",
            headers={"X-Master-Key": settings.oseta_master_key},
        )
        assert resp.status_code == 404
