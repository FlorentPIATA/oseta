# OSETA — Product Context

## Product Name
OSETA — Observatory for Strategic Emerging Technologies & Analytics

## Product Purpose
A financial intelligence dashboard that surfaces cross-sector ETF correlations, macro signals,
and lag-based leading indicators. Combines statistical rigor with LLM-generated plain-English
narratives so two very different audiences can extract value from the same interface.

## Register
product

## Users

### Primary — Common/Informed User
Financial enthusiasts, retail investors, Reddit readers, newsletter subscribers.
- Arrives from a shared link or social post
- No statistics background
- Wants to understand what's happening in the market in plain English
- Success: "I learned something I can act on or share in 60 seconds"
- Mental model: Bloomberg TV headline, not Bloomberg Terminal

### Secondary — Quant/Professional User
Analysts, portfolio managers, systematic traders, researchers.
- Arrives with a specific signal they want to verify
- Needs r-values, p-values, lag days, sample sizes, methodology
- Success: "I can reproduce this and decide if it's tradeable"
- Mental model: research paper supplementary table, not a news app

### Both audiences — same interface, same view
Progressive disclosure bridges them: narrative on the surface, statistics always present
but secondary, full quant detail available on expand. Neither audience is blocked.

## Brand Tone
- Authoritative without being academic
- Precise without being cold
- Plain English first, numbers available — never the reverse
- No hype, no urgency, no gamification
- Credibility through transparency (show methodology, show track record)

## Anti-References
- Bloomberg Terminal (too dense, opaque, no narrative)
- Robinhood / retail brokerage apps (too casual, gamified, no depth)
- Crypto dashboards (neon on black, over-animated, low credibility)
- Generic SaaS analytics (generic card grids, identical metric blocks)
- Financial news sites (ad-heavy, clickbait headlines, no data depth)

## Strategic Principles
1. Story first, data always present — never data without story or story without data
2. Trust through numbers — every narrative claim is backed by visible stats
3. Progressive disclosure — common users read headlines, quants expand for methodology
4. Lag is the product — the leading-indicator relationship is the core value proposition
5. Credibility over excitement — accuracy percentage and p-values build more trust than animations

## Key Features (current MVP)
- Cross-sector correlation heatmap (9 SPDR ETFs)
- Top signal insight card (highest-r significant lag correlation)
- Pipeline admin panel (run ETF/FRED data refresh)
- LLM-generated narratives (publisher service, daily briefing)

## Planned Features (from UX Brain session)
- "Who leads who" directed graph (Cytoscape.js)
- Macro overlay chart (ETF + FRED dual-axis)
- Signal feed (top 5 signals, expandable quant details)
- Track record board (prediction accuracy)
- Sector momentum bars
- Full progressive disclosure pattern across all components

## Color Notes
Not navy + gold (finance cliché). Not neon on black (crypto). The scene: an analyst
at a desktop monitor in a quiet office at 8am, cross-referencing sector moves before
market open — needs to feel credible, calm, and precise. Color serves data legibility,
not brand expression.
