"""Tests d'intégration — /articles (routes/articles.py).

Les appels LLM sont mockés via unittest.mock.patch (services externes).
La DB est réelle (oseta_test via conftest).
"""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from models.db import Article, Source
from models.enums import ArticleStatus
from prompts.analyze import ArticleAnalysisOutput
from prompts.score_impact import ImpactScoreOutput


def _mock_analysis() -> ArticleAnalysisOutput:
    return ArticleAnalysisOutput(
        summary_micro="TSMC limits AI chip production.",
        summary_meso=(
            "TSMC announced capacity constraints affecting Nvidia and AMD chip orders. "
            "The shortage is expected to impact AI infrastructure deployments."
        ),
        key_entities=["TSMC", "Nvidia", "AMD"],
        sector_tags=["Technology", "Semiconductors"],
        sentiment=0.1,
        disruption_level="high",
        leading_indicators=["job postings"],
        weak_signals=["cross-sector supply tension"],
        confidence=0.85,
        manipulation_warning=False,
    )


def _mock_impact() -> ImpactScoreOutput:
    return ImpactScoreOutput(
        strategic_importance_raw=8.0,
        strategic_justification="Critical semiconductor supply constraint.",
        sectors_impacted_count=3,
        has_historical_precedent=True,
        historical_reference="2021 chip shortage",
        risk_level="high",
        recommended_action="alert",
    )


async def _seed_article(session: AsyncSession, content: str = "x" * 300, url: str = "https://example.com/a") -> int:
    source = Source(name="test_source", type="news", reliability=0.8, is_active=True)
    session.add(source)
    await session.flush()
    article = Article(
        source_id=source.id,
        title="TSMC AI chip shortage intensifies",
        content=content,
        url=url,
        sector_tag="Technology",
        status=str(ArticleStatus.RAW),
    )
    session.add(article)
    await session.flush()
    return article.id  # type: ignore[return-value]


class TestListArticles:
    async def test_empty_db_returns_200(self, client: AsyncClient) -> None:
        resp = await client.get("/articles")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0
        assert resp.json()["items"] == []

    async def test_filter_by_status(self, client: AsyncClient, session: AsyncSession) -> None:
        await _seed_article(session)
        await session.commit()

        assert (await client.get("/articles?status=raw")).json()["total"] == 1
        assert (await client.get("/articles?status=published")).json()["total"] == 0

    async def test_pagination_limit_respected(self, client: AsyncClient, session: AsyncSession) -> None:
        source = Source(name="bulk_src", type="news", reliability=0.7, is_active=True)
        session.add(source)
        await session.flush()
        for i in range(5):
            session.add(Article(
                source_id=source.id, title=f"Article {i}", content="x" * 100,
                url=f"https://example.com/{i}", status=str(ArticleStatus.RAW),
            ))
        await session.commit()

        resp = await client.get("/articles?limit=3")
        assert len(resp.json()["items"]) == 3
        assert resp.json()["total"] == 5


class TestGetArticle:
    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        assert (await client.get("/articles/99999")).status_code == 404

    async def test_found_returns_article(self, client: AsyncClient, session: AsyncSession) -> None:
        article_id = await _seed_article(session)
        await session.commit()

        resp = await client.get(f"/articles/{article_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == article_id


class TestAnalyzeArticle:
    async def test_not_found_returns_404(self, client: AsyncClient) -> None:
        assert (await client.post("/articles/99999/analyze")).status_code == 404

    async def test_too_short_content_is_rejected(self, client: AsyncClient, session: AsyncSession) -> None:
        article_id = await _seed_article(session, content="Too short.")
        await session.commit()

        resp = await client.post(f"/articles/{article_id}/analyze")
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

    async def test_analyze_assigns_ci_is_scores(self, client: AsyncClient, session: AsyncSession) -> None:
        article_id = await _seed_article(session)
        await session.commit()

        with (
            patch("services.analyzer._llm_analyze", return_value=_mock_analysis()),
            patch("services.analyzer._llm_score_impact", return_value=_mock_impact()),
        ):
            resp = await client.post(f"/articles/{article_id}/analyze")

        assert resp.status_code == 200
        data = resp.json()
        assert data["ci_score"] is not None
        assert data["is_score"] is not None
        assert data["status"] in ("scored", "published", "rejected")

    async def test_analyze_stores_llm_analysis_json(self, client: AsyncClient, session: AsyncSession) -> None:
        article_id = await _seed_article(session)
        await session.commit()

        with (
            patch("services.analyzer._llm_analyze", return_value=_mock_analysis()),
            patch("services.analyzer._llm_score_impact", return_value=_mock_impact()),
        ):
            await client.post(f"/articles/{article_id}/analyze")

        resp = await client.get(f"/articles/{article_id}")
        analysis = resp.json()["llm_analysis"]
        assert analysis is not None
        assert "summary_meso" in analysis
        assert "ci_total" in analysis


class TestCollectArticles:
    async def test_forbidden_without_master_key(self, client: AsyncClient) -> None:
        assert (await client.post("/articles/collect")).status_code == 403

    async def test_forbidden_with_wrong_key(self, client: AsyncClient) -> None:
        resp = await client.post("/articles/collect", headers={"X-Master-Key": "wrong"})
        assert resp.status_code == 403
