"""Tests unitaires — compute_ci et compute_is (services/scorer.py).

Tests purs sans DB : les formules sont déterministes et auditables.
"""

from datetime import datetime, timedelta, timezone

from models.enums import RiskLevel
from prompts.score_impact import ImpactScoreOutput
from services.scorer import compute_ci, compute_is


def _make_impact(
    strategic: float = 7.0,
    action: str = "watch",
    precedent: bool = False,
    risk: str = "moderate",
) -> ImpactScoreOutput:
    return ImpactScoreOutput(
        strategic_importance_raw=strategic,
        strategic_justification="Test justification.",
        sectors_impacted_count=2,
        has_historical_precedent=precedent,
        risk_level=risk,
        recommended_action=action,
    )


class TestComputeCI:
    def test_reliable_fresh_source_is_published(self):
        ci = compute_ci(
            source_reliability=0.9,
            cross_source_count=3,
            published_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        assert ci.is_published is True
        assert ci.total >= 65.0

    def test_contradiction_lowers_score(self):
        kwargs = dict(
            source_reliability=0.8,
            cross_source_count=2,
            published_at=datetime.now(timezone.utc),
        )
        base = compute_ci(**kwargs, has_contradiction=False)
        penalized = compute_ci(**kwargs, has_contradiction=True)

        assert penalized.total < base.total
        assert penalized.contradiction_penalty == 0.60

    def test_no_primary_source_caps_at_50(self):
        ci = compute_ci(
            source_reliability=1.0,
            cross_source_count=5,
            published_at=datetime.now(timezone.utc),
            has_primary_source=False,
        )
        assert ci.total <= 50.0
        assert ci.is_published is False

    def test_new_source_halves_score(self):
        kwargs = dict(
            source_reliability=0.8,
            cross_source_count=2,
            published_at=datetime.now(timezone.utc),
        )
        normal = compute_ci(**kwargs, source_age_days=365)
        new_src = compute_ci(**kwargs, source_age_days=30)

        # Pénalité × 0.5 → new_src doit être < 60% du score normal
        assert new_src.total < normal.total * 0.6

    def test_no_date_applies_freshness_penalty(self):
        with_date = compute_ci(
            source_reliability=0.8,
            cross_source_count=2,
            published_at=datetime.now(timezone.utc),
        )
        no_date = compute_ci(
            source_reliability=0.8,
            cross_source_count=2,
            published_at=None,
        )
        assert no_date.freshness == 30.0
        assert no_date.total < with_date.total

    def test_score_bounded_between_0_and_100(self):
        worst = compute_ci(
            source_reliability=0.0,
            cross_source_count=0,
            published_at=None,
            has_contradiction=True,
            has_primary_source=False,
        )
        assert 0.0 <= worst.total <= 100.0

    def test_publish_threshold_is_65(self):
        # Juste sous le seuil → non publié
        ci_low = compute_ci(
            source_reliability=0.3,
            cross_source_count=1,
            published_at=datetime.now(timezone.utc) - timedelta(days=20),
        )
        # Juste au-dessus → publié
        ci_high = compute_ci(
            source_reliability=0.9,
            cross_source_count=3,
            published_at=datetime.now(timezone.utc),
        )
        assert ci_low.is_published is (ci_low.total >= 65.0)
        assert ci_high.is_published is (ci_high.total >= 65.0)


class TestComputeIS:
    def test_high_strategic_with_many_sources_triggers_alert(self):
        # 4 sources uniques + strategic=9.5 + action="action" dépasse IS=80
        impact = _make_impact(strategic=9.5, action="action")
        is_score = compute_is(
            llm_output=impact,
            sector_tags=["Technology", "Financials", "Energy"],
            source_domains=["reuters.com", "ft.com", "bloomberg.com", "wsj.com"],
        )
        assert is_score.alert_required is True
        assert is_score.total >= 80.0

    def test_single_sector_gives_min_breadth(self):
        is_score = compute_is(
            llm_output=_make_impact(strategic=5.0),
            sector_tags=["Technology"],
            source_domains=["techcrunch.com"],
        )
        assert is_score.tech_breadth == 20.0

    def test_four_sectors_gives_80_breadth(self):
        is_score = compute_is(
            llm_output=_make_impact(strategic=5.0),
            sector_tags=["Technology", "Financials", "Energy", "Health Care"],
            source_domains=["reuters.com"],
        )
        assert is_score.tech_breadth == 80.0

    def test_score_bounded_between_0_and_100(self):
        is_score = compute_is(
            llm_output=_make_impact(strategic=1.0, action="monitor", risk="low"),
            sector_tags=[],
            source_domains=[],
        )
        assert 0.0 <= is_score.total <= 100.0

    def test_risk_level_mapped_from_llm_output(self):
        is_score = compute_is(
            llm_output=_make_impact(risk="critical"),
            sector_tags=["Technology"],
            source_domains=["reuters.com"],
        )
        assert is_score.risk_level == RiskLevel.CRITICAL

    def test_low_strategic_no_alert(self):
        is_score = compute_is(
            llm_output=_make_impact(strategic=2.0, action="monitor", risk="low"),
            sector_tags=["Technology"],
            source_domains=["techcrunch.com"],
        )
        assert is_score.alert_required is False

    def test_source_diversity_capped_at_100(self):
        is_score = compute_is(
            llm_output=_make_impact(),
            sector_tags=["Technology"],
            source_domains=[f"source{i}.com" for i in range(10)],
        )
        assert is_score.source_diversity == 100.0
