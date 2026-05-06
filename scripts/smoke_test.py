"""OSETA — Smoke test for a deployed API.

Usage: python scripts/smoke_test.py https://oseta-api.onrender.com
Exits 0 on success, 1 on any assertion failure.
"""

import sys

import httpx


def run(base_url: str) -> None:
    base_url = base_url.rstrip("/")

    with httpx.Client(timeout=30.0) as client:
        # ── /health ──────────────────────────────────────────────────────────
        resp = client.get(f"{base_url}/health")
        assert resp.status_code == 200, f"/health returned {resp.status_code}"
        health = resp.json()
        assert health["status"] in ("ok", "degraded"), (
            f"Unexpected health status: {health['status']}"
        )
        print(f"[OK] /health → {health['status']}")

        # ── /correlations/matrix ─────────────────────────────────────────────
        resp = client.get(f"{base_url}/correlations/matrix")
        assert resp.status_code == 200, f"/correlations/matrix returned {resp.status_code}"
        matrix = resp.json()

        significant_with_lag = [
            c for c in matrix["cells"]
            if c["is_significant"] and c["lag_days"] > 0
        ]
        assert len(significant_with_lag) >= 3, (
            f"Expected ≥3 significant lag correlations, got {len(significant_with_lag)}"
        )
        print(
            f"[OK] /correlations/matrix → {len(matrix['cells'])} pairs, "
            f"{len(significant_with_lag)} significant with lag"
        )

        top = max(significant_with_lag, key=lambda c: abs(c["correlation"]))
        print(
            f"[INFO] Top: {top['sector_a_code']}→{top['sector_b_code']} "
            f"r={top['correlation']:.2f} lag={top['lag_days']}d "
            f"p={top.get('p_value', '?')}"
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/smoke_test.py <base_url>")
        sys.exit(1)

    try:
        run(sys.argv[1])
        print("[PASS] All smoke tests passed.")
    except AssertionError as exc:
        print(f"[FAIL] {exc}")
        sys.exit(1)
    except Exception as exc:
        print(f"[ERROR] {exc}")
        sys.exit(1)
