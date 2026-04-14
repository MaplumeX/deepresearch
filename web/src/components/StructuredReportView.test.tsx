import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StructuredReportView } from "./StructuredReportView";
import type { StructuredReport } from "../types/research";


const report: StructuredReport = {
  title: "Research Report",
  summary: "- 摘要结论 [Sabc12345]",
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
      title: "Known Source",
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
      title: "Known Source",
      url: "https://example.com",
      snippet: "Fact",
      providers: ["tavily"],
      acquisition_method: "http_fetch",
      fetched_at: "2026-04-14T08:00:00+00:00",
      is_cited: true,
    },
  ],
};

describe("StructuredReportView", () => {
  it("renders sections and source cards with citation anchors", () => {
    render(<StructuredReportView report={report} />);

    expect(screen.getByText("执行摘要")).toBeInTheDocument();
    expect(screen.getByText("Analysis")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Sabc12345" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Sabc12345" })[0]).toHaveAttribute("href", "#source-Sabc12345");
    expect(screen.getByRole("link", { name: "Known Source" })).toHaveAttribute("href", "https://example.com");
    expect(screen.getByText("已引用")).toBeInTheDocument();
  });
});
