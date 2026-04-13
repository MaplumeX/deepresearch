# brainstorm: improve web search capability

## Goal

Improve the project's web search capability so each research task retrieves higher-quality sources and produces stronger evidence for the final report, while preserving the current deep research workflow shape.

## What I already know

* The backend already has a search pipeline: `rewrite_queries -> search_and_rank -> fetch_and_filter -> extract_and_score -> emit_results`.
* `app/tools/search.py` currently uses Tavily only, runs one `client.search(...)` call per query, hardcodes `search_depth="advanced"`, and only passes `max_results`.
* Search results are deduplicated only by URL, then re-ranked by local keyword heuristics in `app/services/research_worker.py`.
* Page fetching is a second step via `app/tools/fetch.py`, using `httpx` or `urllib`, and content extraction is local via `trafilatura` in `app/tools/extract.py`.
* If `TAVILY_API_KEY` or the Tavily package is missing, `search_web()` returns an empty list and the graph still completes through deterministic fallback paths.
* The frontend run form currently exposes only `question`, `scope`, `output_language`, `max_iterations`, and `max_parallel_tasks`; there is no search-specific control in the request contract.
* README still describes the worker as a scaffold, although query rewrite, ranking, page filtering, and evidence scoring already exist in a first version.

## Assumptions (temporary)

* The request is about improving search quality and search-driven evidence collection, not just polishing the UI.
* We should keep graceful degradation when Tavily credentials are absent.
* A small, high-leverage MVP is preferable to a full multi-provider research agent rewrite.
* The user is interested in a multi-channel search direction rather than a single-provider quality tweak only.

## Open Questions

* None currently blocking. Await final confirmation before implementation.

## Requirements (evolving)

* Improve source retrieval quality for each research task.
* Keep the current research run API and graph contracts stable unless there is a clear gain from changing them.
* Preserve deterministic fallback behavior when live search is unavailable.
* Keep the solution testable with unit coverage around pure ranking/filtering or request-shaping logic.
* Support a path toward multi-channel search instead of keeping search hard-coded to a single provider forever.
* The chosen MVP direction is multi-provider aggregation rather than single-provider tuning only.
* The chosen provider pair is `Tavily + Brave`.
* The task may also refactor fetch and extract stages when it materially improves end-to-end evidence quality.
* The chosen fetch/extract scope is `F3`: a larger content pipeline rewrite with provider-aware strategies.
* The chosen metadata boundary is `P2`: upgrade backend domain models to carry provider/content-acquisition metadata, without committing to broad frontend exposure in this task.

## Acceptance Criteria (evolving)

* [ ] The chosen MVP produces a clearly stronger search pipeline than the current `query -> Tavily search -> local rank` flow.
* [ ] The behavior is covered by targeted tests.
* [ ] Existing research runs still succeed when search credentials are unavailable.
* [ ] Search results from multiple providers can be normalized into the current `SearchHit`-based worker pipeline.
* [ ] The fetch/extract path still degrades gracefully when one provider-specific content path fails.
* [ ] The rewritten content pipeline can choose different acquisition/extraction strategies based on provider or source characteristics.
* [ ] Backend domain models preserve enough provider/content metadata to support future extension without another deep refactor.

## Definition of Done (team quality bar)

* Tests added or updated where appropriate
* Lint, typecheck, and relevant test suites pass
* Docs or notes updated if contracts or behavior change
* Rollout and failure behavior considered for search-provider outages

## Out of Scope (explicit)

* Full browser-agent autonomy across arbitrary sites
* Replacing the whole research graph architecture
* Adding unrelated report-writing or frontend redesign work unless required by the chosen MVP

## Technical Notes

* Relevant files inspected:
  * `app/tools/search.py`
  * `app/tools/fetch.py`
  * `app/tools/extract.py`
  * `app/services/research_worker.py`
  * `app/graph/subgraphs/research_worker.py`
  * `app/config.py`
  * `app/domain/models.py`
  * `web/src/components/RunForm.tsx`
  * `tests/unit/test_research_worker_service.py`
* Current hard constraints:
  * Search provider is Tavily-only today.
  * Search settings are mostly global env config, not request-level controls.
  * Runtime contract explicitly expects the worker to tolerate empty search/fetch output.
* External capability notes from Tavily official docs:
  * Search API supports `topic`, `time_range`, `start_date`, `end_date`, `include_domains`, `exclude_domains`, `include_raw_content`, `auto_parameters`, and `exact_match`.
  * Extract API can return cleaned page content for chosen URLs and can rerank extracted chunks against a query.
* External capability notes from other official docs:
  * Brave Search API exposes a direct web search endpoint with pagination, freshness filtering, country/language targeting, extra snippets, and optional custom reranking via Goggles.
  * SerpApi's Google Search API exposes Google-oriented localization, verticals, pagination, and broad SERP metadata, but normalization cost is higher because the payload is richer and Google-shaped.
  * Exa Search can return search results plus parsed page contents, and also offers deeper research-oriented endpoints, but it starts overlapping with the project's later-stage fetch/extract flow.
* Feasible approaches here:
  * **Approach A: Retrieval-quality MVP** (recommended)
    * Extend backend search request shaping and ranking only.
    * Likely work: richer Tavily params, more candidate collection, better domain/diversity heuristics, optional Tavily extract fallback for selected hits.
    * Pros: highest leverage, limited surface area, fits current architecture.
    * Cons: user cannot steer search behavior directly from UI.
  * **Approach B: Search-control MVP**
    * Add request-level knobs such as preferred domains, freshness, or search mode and thread them through backend + UI.
    * Pros: explicit control, visible product value.
    * Cons: larger API/frontend surface and more validation work.
  * **Approach C: Search-runtime refactor**
    * Introduce provider abstraction or iterative search/extract/crawl stages.
    * Pros: best long-term extensibility.
    * Cons: much bigger task, more cross-layer risk, slower to land.
  * **Approach D: Query-planning MVP**
    * Generate different query intents for each task, such as definition, comparison, implementation, benchmark, and official docs.
    * Pros: improves recall without changing the external API.
    * Cons: can increase noise unless ranking and dedupe also improve.
  * **Approach E: Source-policy MVP**
    * Add source quality rules such as official-domain priority, domain diversity, blacklist/whitelist, freshness weighting, and duplicate-host suppression.
    * Pros: directly improves evidence trustworthiness.
    * Cons: requires explicit heuristics and careful tests to avoid over-filtering.
  * **Approach F: Extraction-quality MVP**
    * Use Tavily raw/extract capabilities for selected hits before falling back to local fetch plus `trafilatura`.
    * Pros: raises the chance of getting usable article text from dynamic or noisy pages.
    * Cons: provider coupling gets stronger and request cost may increase.
  * **Approach G: Lightweight iterative retrieval**
    * Keep the current architecture but allow a worker-level second retrieval pass when first-pass evidence is weak or one-sided.
    * Pros: addresses sparse evidence without a full runtime rewrite.
    * Cons: adds control-flow complexity and may increase latency.
  * **Approach H: Search evaluation first**
    * Build a small benchmark set and scoring metrics first, then optimize the pipeline against those metrics.
    * Pros: makes later search changes measurable and safer.
    * Cons: user-visible improvements land later unless paired with another MVP.
  * **Approach I: Multi-provider aggregation**
    * Introduce a provider interface and query more than one web-search backend, then merge, dedupe, and rerank results.
    * Pros: strongest recall and provider resilience.
    * Cons: highest integration complexity, cost, and normalization work.
  * **Approach J: Primary + fallback providers**
    * Keep one main provider and call a second provider only when the first returns too few or too-homogeneous results.
    * Pros: better reliability with less complexity than full aggregation.
    * Cons: coverage gains are smaller than always-on aggregation.
  * **Approach K: Source-type channels**
    * Treat channels as intent/source classes, such as official docs, general web, news/blog, community/forum, or academic.
    * Pros: aligns better with research quality goals than "more providers" alone.
    * Cons: requires explicit routing logic and source-policy decisions.

## Decision (ADR-lite)

**Context**: The project currently hard-codes Tavily as the only search provider. The user wants to move toward multi-channel search, and explicitly selected the multi-provider aggregation direction.

**Decision**: Use multi-provider aggregation as the main design direction for this task, narrow MVP to `Tavily + Brave`, redesign the content pipeline at `F3` scope, and adopt `P2` so richer provider/content metadata becomes part of backend domain models.

**Consequences**:

* We likely need a provider abstraction around `app/tools/search.py`.
* Result normalization and dedupe policy become first-class concerns.
* Cost, latency, and failure-handling rules must be explicit because one provider can fail while another still succeeds.
* Search-stage changes and content-stage changes should stay separable so fallback behavior remains understandable.
* Provider-aware content acquisition probably requires richer internal models than the current `SearchHit(title, url, snippet)` only flow.
* API/Frontend changes should stay minimal unless needed to preserve correctness, because `P2` does not require fully exposing internal provider metadata yet.

## Research Notes

### What similar providers support

* **Tavily**: agent-oriented web search with domain filters, time filters, raw content, and extract support.
* **Brave Search API**: independent web index, pagination, language/country targeting, freshness controls, and custom reranking features.
* **SerpApi Google Search API**: strong Google-shaped recall and localization controls, but a broader and more irregular SERP schema.
* **Exa Search**: AI-oriented search plus content retrieval, but overlaps more with the project's fetch/extract stages.

### Constraints from this repo

* Current worker contract expects a simple `SearchHit(title, url, snippet)` list.
* Fetch and extraction are separate stages already implemented locally.
* The current codebase has Tavily dependency only; any new provider should ideally be added with small surface area and HTTP-first integration.
* We should avoid a deep runtime rewrite in the MVP.

### Feasible provider combinations here

* **Combo 1: Tavily + Brave** (recommended)
  * How it works: keep Tavily, add Brave as a second always-on web provider, normalize both into `SearchHit`, then merge and rerank.
  * Pros: two independent web indexes, straightforward HTTP integration, preserves current fetch/extract split.
  * Cons: needs duplicate-host and duplicate-URL policies plus latency budgeting.
* **Combo 2: Tavily + SerpApi(Google)**
  * How it works: pair current agent-oriented search with Google-shaped SERP recall.
  * Pros: potentially stronger mainstream recall and geo coverage.
  * Cons: normalization complexity is higher, payload shape is noisier, and dependency/cost profile is heavier.
* **Combo 3: Tavily + Exa**
  * How it works: pair Tavily search with Exa search or contents.
  * Pros: good fit for AI-research use cases and strong content retrieval options.
  * Cons: search and extraction responsibilities may blur, making MVP boundaries less clean.

### Fetch/extract scope options inside this task

* **Scope F1: Search-only plus local fetch cleanup**
  * Keep fetch/extract architecture mostly unchanged.
  * Only improve parallelism, retries, filtering, and source normalization after multi-provider search.
  * Lowest risk.
* **Scope F2: Hybrid content acquisition** (recommended)
  * Keep local `fetch + trafilatura` as the default backbone.
  * Add provider-native content hints or raw content where useful, and fall back cleanly when unavailable.
  * Best balance of quality and scope.
* **Scope F3: Larger content pipeline rewrite**
  * Redesign fetch/extract around provider-aware content acquisition, richer metadata, and per-source extraction strategies.
  * Highest upside, but likely too large for a focused MVP.

## Technical Approach

1. Introduce a search-provider abstraction and aggregate `Tavily + Brave` results into a richer backend search-hit model with provider metadata.
2. Split the current content stage into explicit phases:
   * search result normalization
   * candidate dedupe / merge
   * content acquisition
   * extraction / normalization
   * evidence scoring input
3. Upgrade backend domain models so search hits and/or source documents can carry:
   * provider identity
   * provider-native ranking hints
   * acquisition method
   * raw snippet / metadata summary needed for downstream decisions
4. Implement provider-aware acquisition strategies, for example:
   * use provider-supplied raw content or extract data when available and trustworthy
   * fall back to direct HTTP fetch
   * then fall back to local extraction cleanup
5. Keep the worker contract resilient:
   * one provider failure must not fail the whole task
   * one acquisition strategy failure must fall through to the next viable path
6. Update scoring/dedupe heuristics to account for cross-provider duplicates and source diversity.
7. Cover the new pure logic with unit tests and preserve no-credentials fallback behavior.

## Implementation Plan (small PRs)

* PR1: Add provider abstraction, richer backend models, and normalized Tavily + Brave search aggregation
* PR2: Rework content acquisition and extraction pipeline with provider-aware fallbacks
* PR3: Update ranking/dedupe/tests/docs and keep runtime contracts coherent
