# brainstorm: improve http fetch capability

## Goal

Improve the project's HTTP fetch capability so research runs can acquire more usable source content from real-world pages with higher success rate, better extraction quality, and clearer fallback behavior.

## What I already know

* The repo already has a basic fetch pipeline in `app/tools/fetch.py`.
* Current fetch flow uses provider raw content first, then `httpx.AsyncClient`, and finally falls back to `urllib` if `httpx` is unavailable.
* Current extraction flow in `app/tools/extract.py` uses `trafilatura` when available, otherwise strips HTML tags with a regex fallback.
* Search providers currently include Tavily, Brave, and Serper in `app/tools/search.py`.
* Current fetch settings are minimal: mainly `FETCH_TIMEOUT_SECONDS` in `app/config.py`.
* Current fetch behavior does not appear to include retry policy, per-site strategy, robots/cookie/session handling, JS rendering, anti-bot handling, or readability-oriented extraction alternatives beyond `trafilatura`.

## Assumptions (temporary)

* The main problem is not "no fetch at all", but weak coverage for dynamic pages, anti-bot pages, and low-quality extraction on messy HTML.
* The project should preserve deterministic fallback behavior when premium services or optional dependencies are absent.
* Any new capability should fit the existing separation where graph nodes own state changes and tools/services stay focused.

## Open Questions

* Is the scoped MVP below acceptable for implementation, or should it stay at design/proposal stage only?

## Requirements (evolving)

* Evaluate practical approaches to improve fetch success and extraction quality.
* Compare "improve current stack" vs "add new library/service" options.
* Recommend an MVP path that matches current repo constraints.
* Identify candidate providers/frameworks/sites worth integrating or targeting first.
* Use strengthened native HTTP fetching as the default path.
* Add Firecrawl and Jina Reader as external capability layers.

## Acceptance Criteria (evolving)

* [ ] Existing fetch pipeline and constraints are documented in this PRD.
* [ ] At least 2-3 feasible improvement approaches are compared with trade-offs.
* [ ] A recommended MVP direction is selected or ready for user selection.
* [ ] If implementation proceeds, the chosen approach has clear code touchpoints and validation scope.

## Definition of Done (team quality bar)

* Tests added/updated (unit/integration where appropriate)
* Lint / typecheck / CI green
* Docs/notes updated if behavior changes
* Rollout/rollback considered if risky

## Out of Scope (explicit)

* General crawler platform redesign beyond fetch/extract capability
* Large-scale queueing/distributed crawling infrastructure
* Production-grade browser farm design unless explicitly chosen

## Technical Notes

* Existing fetch code: `app/tools/fetch.py`
* Existing extract code: `app/tools/extract.py`
* Existing search providers: `app/tools/search.py`
* Existing fetch config: `app/config.py`
* Existing content filtering already rejects page-like content under 200 chars in `app/services/research_worker.py`.
* Existing scoring already treats `provider_raw_content` as stronger than `http_fetch`, and `search_snippet` as weakest.

## Research Notes

### What similar tools do

* Tavily already offers an `extract` endpoint that returns page content in `markdown` or `text`, supports `basic`/`advanced` extraction depth, and configurable timeouts.
* Firecrawl exposes a `scrape` API that can return `markdown`, `html`, `rawHtml`, `json`, `links`, and screenshots, and explicitly handles proxies, rate limits, JS-blocked pages, and dynamic content.
* Browserless offers HTTP-first browser APIs. Its `smart-scrape` endpoint automatically escalates from lightweight HTTP fetch to proxy, then headless browser, then captcha solving; `unblock` can return content, cookies, or a browser WebSocket endpoint for continued automation.
* Jina Reader turns a URL into LLM-friendly content with a simple Reader API, and supports browser engine selection, wait-for selectors, JSON response mode, and higher-quality ReaderLM-v2 conversion.
* Crawl4AI is an in-process browser crawling framework with markdown generation, content filters, JS execution, `wait_for`, and session reuse for dynamic multi-step pages.
* `curl_cffi` focuses on transport-level browser impersonation and can impersonate current browser fingerprints such as the latest Chrome/Safari targets supported by the library.

### Constraints from our repo/project

* The repo is already Python-first and async-first for fetch/search flow.
* The current pipeline is intentionally simple and has deterministic fallbacks when richer providers or dependencies are unavailable.
* Current data model already distinguishes `provider_raw_content`, `http_fetch`, and `search_snippet`, so adding more acquisition tiers is feasible.
* The lowest-friction improvement is one that fits inside `app/tools/fetch.py` and preserves `app/tools/extract.py` contracts.

### Feasible approaches here

**Approach A: strengthen the current HTTP pipeline** (Recommended baseline)

* How it works:
  Keep `httpx` as the default fetch path, add retries/backoff, stricter content-type handling, better charset handling, optional `curl_cffi` transport for browser impersonation, and a richer extraction fallback chain.
  Reuse Tavily more deeply by calling Tavily Extract for URLs when a Tavily key is present.
* Pros:
  Low code churn, fits existing architecture, preserves deterministic fallback, cheapest operationally, easiest to test.
* Cons:
  Still limited for true JS-heavy pages and hard anti-bot targets.

**Approach B: add an in-process browser crawler**

* How it works:
  Introduce Crawl4AI as an optional dynamic-page fetcher for domains or failures that need rendering, waiting, clicking, or session reuse.
* Pros:
  Strong fit for Python stack, built-in markdown generation, dynamic page interaction, reusable sessions, fewer custom Playwright wrappers.
* Cons:
  Heavier runtime, browser install overhead, slower fetches, more infra complexity than pure HTTP.

**Approach C: add a managed fetch fallback service**

* How it works:
  Route difficult URLs to a hosted service such as Firecrawl, Browserless, Jina Reader, or ZenRows depending on the problem type.
* Pros:
  Fastest path to higher success rate on difficult sites, offloads anti-bot and browser infrastructure, can return markdown/HTML/structured data directly.
* Cons:
  External dependency, cost, vendor-specific response contracts, weaker offline/deterministic behavior.

### Preliminary recommendation

* MVP should start with Approach A plus one optional managed fallback.
* If we want the smallest delta, Tavily Extract is the first service to try because Tavily is already in the repo and already returns extraction-oriented content.
* If the real pain is JS rendering and anti-bot, Browserless Smart Scrape or Firecrawl is a stronger fallback than expanding pure HTTP heuristics forever.
* If we expect repeated interactive flows inside the repo itself, prefer Crawl4AI over raw Playwright because it already gives markdown generation, waiting, sessions, and crawler-oriented abstractions.

### User-selected direction

* Selected stack direction: Approach A + Firecrawl + Jina Reader.
* Working interpretation:
  Default path stays in-process and low-cost.
  Jina Reader is the lightweight remote reader/extractor layer.
  Firecrawl is the heavier high-success fallback for dynamic pages, structured extraction, and action-driven pages.
* Firecrawl should be used only as the last fallback after native HTTP and Jina Reader both fail.

### Proposed fetch tiering

* Tier 0: keep provider raw content when already available and sufficiently long.
* Tier 1: use strengthened in-process HTTP fetch as the default acquisition path.
* Tier 2: use Jina Reader when Tier 1 returns weak extraction, blocked pages, or very noisy HTML.
* Tier 3: use Firecrawl only when Tier 1 and Tier 2 both fail to produce acceptable content.

### Working MVP scope

* Add minimal routing heuristics instead of a full per-domain policy engine.
* Add explicit acquisition methods for Jina Reader and Firecrawl so downstream audit/synthesis can distinguish source quality.
* Start with read-only Firecrawl scrape usage; defer login/session automation unless it becomes a real requirement.
* Optimize the first pass primarily for news/article sites.
* Prioritize Chinese news/article sites for the MVP.
* Include platform-like Chinese media/article sources such as WeChat articles, Zhihu columns, 36Kr, and Huxiu in the first batch.

### Scoped MVP draft

* Keep search provider layer unchanged for the first implementation pass.
* Upgrade only the fetch/extract path and related scoring metadata.
* Add native HTTP quality-failure detection tuned for Chinese article pages.
* Add optional Jina Reader fallback for weak extraction or article-interstitial pages.
* Add optional Firecrawl fallback only after native HTTP and Jina Reader both fail.
* Preserve deterministic local fallback behavior when external API keys are absent.
* Defer domain-specific rule tables, login/session flows, and browser automation beyond Firecrawl scrape.

### Implementation draft

* Add a local extraction pipeline with three stages:
  `selectolax` for HTML cleanup and interstitial detection,
  `trafilatura` as the primary article extractor,
  `readability-lxml` as the fallback article extractor before plain-text stripping.
* Keep remote tiers outside the extractor itself:
  native HTTP acquires HTML,
  local extractor decides whether content is acceptable,
  Jina Reader and Firecrawl are only escalation paths when local quality fails.
* Introduce fetch outcome metadata so later scoring/audit can distinguish:
  transport success,
  extraction success,
  escalation reason,
  final acquisition method,
  detected interstitial/block-page markers.
* Tune the first-pass heuristics for Chinese article pages and mixed media/article platforms.

### Candidate code touchpoints

* `app/tools/fetch.py`
  Add fetch routing, escalation decision points, and external fallback clients.
* `app/tools/extract.py`
  Replace the single extractor path with a staged local extraction pipeline.
* `app/domain/models.py`
  Extend acquisition method literals and optional metadata fields if needed.
* `app/config.py`
  Add feature flags, API keys, and extraction/failure threshold settings.
* `tests/unit/test_extract_tool.py`
  Add unit coverage for staged extractor selection and quality-failure cases.
* `tests/unit/test_research_worker_service.py`
  Update or extend tests that depend on page-content thresholds and scoring.

### Selected failure policy

* Selected policy: quality failure, not just transport failure.
* Draft escalation rule:
  Escalate from native HTTP to Jina Reader, and from Jina Reader to Firecrawl, when the result is empty, request-level failure, extracted main content remains too short, or the page looks like a block/interstitial page instead of useful source content.
* Initial heuristics should align with existing repo thresholds:
  Treat sub-200-character page content as failed page acquisition unless it is intentionally snippet-like.
  Detect obvious block pages using small keyword rules such as captcha, access denied, verify you are human, enable javascript, and similar interstitial markers.
