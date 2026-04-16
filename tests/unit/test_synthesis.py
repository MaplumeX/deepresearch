from __future__ import annotations

import unittest
from unittest.mock import patch

from app.config import Settings
from app.domain.models import ReportDraft, ReportSectionDraft
from app.services.synthesis import (
    _build_compact_payload,
    _normalize_task_heading,
    assign_report_headings,
    synthesize_report,
)


class SynthesisServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key=None,
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            serper_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=False,
        )

    def test_fallback_synthesis_uses_summary_task_sections_and_conclusion(self) -> None:
        report = synthesize_report(
            question="Can you continue this analysis?",
            tasks=[{"task_id": "task-1", "title": "Assess topic coverage"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Fact",
                    "snippet": "Fact",
                    "source_id": "Ssource001",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                }
            ],
            sources={
                "Ssource001": {
                    "title": "Source",
                    "url": "https://example.com",
                    "content": "Fact",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                }
            },
            settings=self.settings,
            memory={
                "rolling_summary": "Earlier turns narrowed the scope to runtime memory.",
                "recent_turns": [],
                "key_facts": [],
                "open_questions": [],
            },
            output_language="en",
        )

        self.assertEqual(report.title, "Research Report")
        self.assertIn("## Summary", report.markdown)
        self.assertIn("## Topic coverage", report.markdown)
        self.assertIn("## Conclusion", report.markdown)
        self.assertNotIn("## Conversation Context", report.markdown)
        self.assertEqual(report.cited_source_ids, ["Ssource001"])
        self.assertEqual(report.citation_index[0].source_id, "Ssource001")
        self.assertEqual(report.source_cards[0].source_id, "Ssource001")
        self.assertEqual(report.sections[0].heading, "Summary")
        self.assertEqual(report.sections[1].heading, "Topic coverage")
        self.assertEqual(report.sections[2].heading, "Conclusion")

    def test_fallback_synthesis_uses_task_sections_and_risks(self) -> None:
        report = synthesize_report(
            question="How should we evaluate deep research coverage?",
            tasks=[{"task_id": "task-1", "title": "Evaluate deep research coverage"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "A case study reduced citation errors by 32 percent.",
                    "snippet": "A case study reduced citation errors by 32 percent.",
                    "source_id": "Sexample",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-1",
                    "claim": "Low-diversity sources can still bias the report.",
                    "snippet": "Low-diversity sources can still bias the report.",
                    "source_id": "Srisk",
                    "evidence_type": "risk",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
            ],
            sources={
                "Sexample": {
                    "title": "Example",
                    "url": "https://example.com/example",
                    "content": "A case study reduced citation errors by 32 percent.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srisk": {
                    "title": "Risk",
                    "url": "https://example.com/risk",
                    "content": "Low-diversity sources can still bias the report.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
            },
            settings=self.settings,
            memory=None,
            output_language="en",
        )

        headings = [section.heading for section in report.sections]
        self.assertIn("Deep research coverage", headings)
        self.assertIn("Risks and Limitations", headings)
        self.assertIn("Conclusion", headings)

    def test_compact_payload_excludes_raw_source_content(self) -> None:
        payload = _build_compact_payload(
            question="How should we evaluate deep research coverage?",
            tasks=[{"task_id": "task-1", "title": "Coverage", "question": "Evaluate coverage"}],
            coverage_requirements=[],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "A case study reduced citation errors by 32 percent.",
                    "snippet": "A case study reduced citation errors by 32 percent.",
                    "source_id": "Sexample",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                    "title": "Example",
                    "url": "https://example.com/example",
                }
            ],
            sources={
                "Sexample": {
                    "title": "Example",
                    "url": "https://example.com/example",
                    "content": "Full source content should stay out of synthesis payloads.",
                    "providers": ["tavily"],
                }
            },
            memory_brief="None",
        )

        self.assertIn("Sexample", payload.sources)
        self.assertNotIn("content", payload.sources["Sexample"])
        self.assertIn("snippet", payload.sources["Sexample"])

    def test_synthesis_uses_multi_stage_when_payload_exceeds_soft_limit(self) -> None:
        llm_settings = Settings(
            app_name="test",
            planner_model="test-model",
            synthesis_model="test-model",
            llm_api_key="dummy-key",
            llm_base_url=None,
            tavily_api_key=None,
            brave_api_key=None,
            serper_api_key=None,
            checkpoint_db_path="test.db",
            runs_db_path="test-runs.db",
            fetch_timeout_seconds=1.0,
            default_max_iterations=2,
            default_max_parallel_tasks=3,
            search_max_results=3,
            require_human_review=False,
            enable_llm_planning=False,
            enable_llm_synthesis=True,
            synthesis_soft_char_limit=10,
            synthesis_hard_char_limit=1000,
        )
        staged_draft = ReportDraft(
            title="Research Report",
            summary="- Fact [Ssource001]",
            sections=[
                ReportSectionDraft(
                    heading="Topic",
                    body_markdown="- Fact [Ssource001]",
                ),
                ReportSectionDraft(
                    heading="Conclusion",
                    body_markdown="- Fact [Ssource001]",
                )
            ],
        )

        with patch("app.services.synthesis._maybe_synthesize_single_call") as mock_single, patch(
            "app.services.synthesis._maybe_synthesize_multi_stage",
            return_value=staged_draft,
        ) as mock_multi:
            report = synthesize_report(
                question="Can you continue this analysis?",
                tasks=[{"task_id": "task-1", "title": "Topic", "question": "Continue the analysis"}],
                findings=[
                    {
                        "task_id": "task-1",
                        "claim": "Fact",
                        "snippet": "Fact",
                        "source_id": "Ssource001",
                        "confidence": 0.8,
                        "relevance_score": 0.7,
                    }
                ],
                sources={
                    "Ssource001": {
                        "title": "Source",
                        "url": "https://example.com",
                        "content": "Fact",
                        "providers": ["tavily"],
                        "acquisition_method": "http_fetch",
                        "fetched_at": "2026-04-14T08:00:00+00:00",
                    }
                },
                settings=llm_settings,
                memory=None,
                output_language="en",
            )

        mock_single.assert_not_called()
        mock_multi.assert_called_once()
        self.assertIn("## Summary", report.markdown)
        self.assertIn("## Topic", report.markdown)
        self.assertIn("## Conclusion", report.markdown)

    def test_fallback_synthesis_prefers_coverage_requirement_sections_when_available(self) -> None:
        report = synthesize_report(
            question="How should we evaluate deep research coverage?",
            tasks=[
                {
                    "task_id": "task-1",
                    "title": "Assess topic coverage",
                    "coverage_tags": ["scope", "definitions"],
                },
                {
                    "task_id": "task-2",
                    "title": "Collect recent evidence",
                    "coverage_tags": ["recent", "examples"],
                },
                {
                    "task_id": "task-3",
                    "title": "Analyze tradeoffs",
                    "coverage_tags": ["risks", "tradeoffs"],
                },
            ],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Deep research needs explicit scope boundaries.",
                    "snippet": "Deep research needs explicit scope boundaries.",
                    "source_id": "Sscope",
                    "evidence_type": "definition",
                    "confidence": 0.9,
                    "relevance_score": 0.8,
                },
                {
                    "task_id": "task-2",
                    "claim": "A recent benchmark improved citation precision by 18 percent.",
                    "snippet": "A recent benchmark improved citation precision by 18 percent.",
                    "source_id": "Srecent",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-3",
                    "claim": "Higher coverage usually increases latency and cost.",
                    "snippet": "Higher coverage usually increases latency and cost.",
                    "source_id": "Srisk",
                    "evidence_type": "comparison",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
            ],
            sources={
                "Sscope": {
                    "title": "Scope",
                    "url": "https://example.com/scope",
                    "content": "Deep research needs explicit scope boundaries.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srecent": {
                    "title": "Recent",
                    "url": "https://example.com/recent",
                    "content": "A recent benchmark improved citation precision by 18 percent.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srisk": {
                    "title": "Tradeoff",
                    "url": "https://example.com/tradeoff",
                    "content": "Higher coverage usually increases latency and cost.",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
            },
            settings=self.settings,
            coverage_requirements=[
                {
                    "requirement_id": "scope-terminology",
                    "title": "Scope and terminology",
                    "description": "Clarify scope and key terms.",
                    "coverage_tags": ["scope", "definitions"],
                },
                {
                    "requirement_id": "recent-evidence",
                    "title": "Recent evidence",
                    "description": "Ground the answer in recent evidence and examples.",
                    "coverage_tags": ["recent", "examples"],
                },
                {
                    "requirement_id": "risks-tradeoffs",
                    "title": "Risks and tradeoffs",
                    "description": "Explain risks and tradeoffs.",
                    "coverage_tags": ["risks", "tradeoffs"],
                },
            ],
            memory=None,
            output_language="en",
        )

        headings = [section.heading for section in report.sections]
        self.assertIn("Scope and Terminology", headings)
        self.assertIn("Recent Evidence and Examples", headings)
        self.assertIn("Risks and Limitations", headings)
        self.assertNotIn("Topic coverage", headings)

    def test_fallback_synthesis_localizes_default_coverage_requirement_headings_for_chinese(self) -> None:
        report = synthesize_report(
            question="请继续分析这个问题",
            tasks=[
                {
                    "task_id": "task-1",
                    "title": "评估范围",
                    "coverage_tags": ["scope", "definitions"],
                },
                {
                    "task_id": "task-2",
                    "title": "收集近期证据",
                    "coverage_tags": ["recent", "examples"],
                },
                {
                    "task_id": "task-3",
                    "title": "分析权衡",
                    "coverage_tags": ["risks", "tradeoffs"],
                },
            ],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "需要先明确研究边界。",
                    "snippet": "需要先明确研究边界。",
                    "source_id": "Sscope001",
                    "evidence_type": "definition",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-2",
                    "claim": "近期案例显示引用准确率有所提升。",
                    "snippet": "近期案例显示引用准确率有所提升。",
                    "source_id": "Srecent001",
                    "evidence_type": "example",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-3",
                    "claim": "更高覆盖率通常意味着更高时延。",
                    "snippet": "更高覆盖率通常意味着更高时延。",
                    "source_id": "Srisk001",
                    "evidence_type": "risk",
                    "confidence": 0.7,
                    "relevance_score": 0.6,
                },
            ],
            sources={
                "Sscope001": {
                    "title": "范围来源",
                    "url": "https://example.com/scope",
                    "content": "需要先明确研究边界。",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srecent001": {
                    "title": "近期来源",
                    "url": "https://example.com/recent",
                    "content": "近期案例显示引用准确率有所提升。",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srisk001": {
                    "title": "风险来源",
                    "url": "https://example.com/risk",
                    "content": "更高覆盖率通常意味着更高时延。",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
            },
            settings=self.settings,
            coverage_requirements=[
                {
                    "requirement_id": "scope-terminology",
                    "title": "Scope and terminology",
                    "description": "Clarify scope and terms.",
                    "coverage_tags": ["scope", "definitions"],
                },
                {
                    "requirement_id": "recent-evidence",
                    "title": "Recent evidence",
                    "description": "Ground the answer in recent evidence and examples.",
                    "coverage_tags": ["recent", "examples"],
                },
                {
                    "requirement_id": "risks-tradeoffs",
                    "title": "Risks and tradeoffs",
                    "description": "Explain risks and tradeoffs.",
                    "coverage_tags": ["risks", "tradeoffs"],
                },
            ],
            memory=None,
            output_language="zh-CN",
        )

        headings = [section.heading for section in report.sections]
        self.assertIn("范围与术语", headings)
        self.assertIn("近期证据与案例", headings)
        self.assertIn("风险与局限", headings)

    def test_normalize_task_heading_strips_action_prefixes(self) -> None:
        self.assertEqual(
            _normalize_task_heading({"title": "Recover search coverage for primary sources"}),
            "Search coverage for primary sources",
        )
        self.assertEqual(
            _normalize_task_heading({"title": "评估 OpenAI 与 Anthropic 的研究能力差异"}),
            "OpenAI 与 Anthropic 的研究能力差异",
        )

    def test_assign_report_headings_falls_back_without_overwriting_task_title(self) -> None:
        tasks = assign_report_headings(
            question="请继续分析这个问题",
            tasks=[
                {
                    "task_id": "task-1",
                    "title": "评估研究覆盖质量",
                    "question": "请评估研究覆盖质量。",
                }
            ],
            findings=[],
            settings=self.settings,
            output_language="zh-CN",
        )

        self.assertEqual(tasks[0]["title"], "评估研究覆盖质量")
        self.assertEqual(tasks[0]["report_heading"], "研究覆盖质量")

    def test_assign_report_headings_falls_back_when_llm_headings_conflict(self) -> None:
        with patch(
            "app.services.synthesis._maybe_generate_report_headings_with_llm",
            return_value={
                "task-1": "Coverage quality",
                "task-2": "Coverage quality",
            },
        ):
            tasks = assign_report_headings(
                question="How should we evaluate deep research coverage?",
                tasks=[
                    {
                        "task_id": "task-1",
                        "title": "Assess coverage quality",
                        "question": "Evaluate coverage quality.",
                    },
                    {
                        "task_id": "task-2",
                        "title": "Assess evidence gaps",
                        "question": "Evaluate evidence gaps.",
                    },
                ],
                findings=[],
                settings=self.settings,
                output_language="en",
            )

        self.assertEqual(tasks[0]["report_heading"], "Coverage quality")
        self.assertEqual(tasks[1]["report_heading"], "Evidence gaps")

    def test_fallback_synthesis_prefers_report_heading_for_task_sections(self) -> None:
        report = synthesize_report(
            question="Can you continue this analysis?",
            tasks=[
                {
                    "task_id": "task-1",
                    "title": "Assess topic coverage",
                    "report_heading": "Coverage quality",
                }
            ],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "Fact",
                    "snippet": "Fact",
                    "source_id": "Ssource001",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                }
            ],
            sources={
                "Ssource001": {
                    "title": "Source",
                    "url": "https://example.com",
                    "content": "Fact",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                }
            },
            settings=self.settings,
            memory=None,
            output_language="en",
        )

        self.assertIn("## Coverage quality", report.markdown)
        self.assertNotIn("## Topic coverage", report.markdown)

    def test_fallback_synthesis_localizes_fixed_headings_for_chinese(self) -> None:
        report = synthesize_report(
            question="请继续分析这个问题",
            tasks=[{"task_id": "task-1", "title": "评估研究覆盖质量"}],
            findings=[
                {
                    "task_id": "task-1",
                    "claim": "事实",
                    "snippet": "事实",
                    "source_id": "Ssource001",
                    "confidence": 0.8,
                    "relevance_score": 0.7,
                },
                {
                    "task_id": "task-1",
                    "claim": "存在样本偏差风险。",
                    "snippet": "存在样本偏差风险。",
                    "source_id": "Srisk001",
                    "evidence_type": "risk",
                    "confidence": 0.7,
                    "relevance_score": 0.6,
                },
            ],
            sources={
                "Ssource001": {
                    "title": "来源",
                    "url": "https://example.com",
                    "content": "事实",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
                "Srisk001": {
                    "title": "风险来源",
                    "url": "https://example.com/risk",
                    "content": "存在样本偏差风险。",
                    "providers": ["tavily"],
                    "acquisition_method": "http_fetch",
                    "fetched_at": "2026-04-14T08:00:00+00:00",
                },
            },
            settings=self.settings,
            memory=None,
            output_language="zh-CN",
        )

        headings = [section.heading for section in report.sections]
        self.assertEqual(report.title, "研究报告")
        self.assertIn("## 摘要", report.markdown)
        self.assertIn("## 研究覆盖质量", report.markdown)
        self.assertIn("## 风险与局限", report.markdown)
        self.assertIn("## 结论", report.markdown)
        self.assertIn("## 参考资料", report.markdown)
        self.assertEqual(headings[0], "摘要")


if __name__ == "__main__":
    unittest.main()
