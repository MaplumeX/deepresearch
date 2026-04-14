import { describe, expect, it } from "vitest";

import { linkifyCitations, readReportField, readStructuredReport } from "./report";
import type { ResearchRunResult } from "../types/research";


const structuredResult: ResearchRunResult = {
  final_report: "# Final",
  final_structured_report: {
    title: "Research Report",
    summary: "- Fact [Sabc12345]",
    markdown: "# Research Report",
    sections: [
      {
        section_id: "analysis",
        heading: "Analysis",
        body_markdown: "Fact [Sabc12345]",
        cited_source_ids: ["Sabc12345"],
      },
    ],
    cited_source_ids: ["Sabc12345"],
    citation_index: [
      {
        source_id: "Sabc12345",
        title: "Known",
        url: "https://example.com",
        snippet: "Fact",
        providers: ["tavily"],
        acquisition_method: "http_fetch",
        cited_in_sections: ["analysis"],
        occurrence_count: 1,
        relevance_score: 0.8,
        confidence: 0.9,
      },
    ],
    source_cards: [
      {
        source_id: "Sabc12345",
        title: "Known",
        url: "https://example.com",
        snippet: "Fact",
        providers: ["tavily"],
        acquisition_method: "http_fetch",
        fetched_at: "2026-04-14T08:00:00+00:00",
        is_cited: true,
      },
    ],
  },
};

describe("report helpers", () => {
  it("reads structured report payloads safely", () => {
    const report = readStructuredReport(structuredResult);

    expect(report?.title).toBe("Research Report");
    expect(report?.sections[0]?.heading).toBe("Analysis");
  });

  it("reads markdown report fields", () => {
    expect(readReportField(structuredResult, "final_report")).toBe("# Final");
  });

  it("linkifies inline citations for source anchors", () => {
    expect(linkifyCitations("Fact [Sabc12345]")).toBe("Fact [Sabc12345](#source-Sabc12345)");
  });
});
