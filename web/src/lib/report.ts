import type {
  CitationIndexEntry,
  ReportSection,
  ResearchRunResult,
  SourceCard,
  StructuredReport,
} from "../types/research";


export function readReportField(result: ResearchRunResult | null, key: "draft_report" | "final_report"): string {
  if (!result) {
    return "";
  }
  return asString(result[key]);
}

export function readStructuredReport(result: ResearchRunResult | null): StructuredReport | null {
  if (!result) {
    return null;
  }
  const finalReport = asStructuredReport(result.final_structured_report);
  if (finalReport) {
    return finalReport;
  }
  return asStructuredReport(result.draft_structured_report);
}

export function linkifyCitations(markdown: string): string {
  return markdown.replace(/\[(S[^\]]+)\]/g, "[$1](#source-$1)");
}

function asStructuredReport(value: unknown): StructuredReport | null {
  if (!isRecord(value)) {
    return null;
  }
  const title = asString(value.title);
  const summary = asString(value.summary);
  const markdown = asString(value.markdown);
  const sections = asReportSections(value.sections);
  const citedSourceIds = asStringArray(value.cited_source_ids);
  const citationIndex = asCitationIndex(value.citation_index);
  const sourceCards = asSourceCards(value.source_cards);
  if (!title || !markdown) {
    return null;
  }
  return {
    title,
    summary,
    markdown,
    sections,
    cited_source_ids: citedSourceIds,
    citation_index: citationIndex,
    source_cards: sourceCards,
  };
}

function asReportSections(value: unknown): ReportSection[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }
    const sectionId = asString(item.section_id);
    const heading = asString(item.heading);
    const bodyMarkdown = asString(item.body_markdown);
    if (!sectionId || !heading) {
      return [];
    }
    return [
      {
        section_id: sectionId,
        heading,
        body_markdown: bodyMarkdown,
        cited_source_ids: asStringArray(item.cited_source_ids),
      },
    ];
  });
}

function asCitationIndex(value: unknown): CitationIndexEntry[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }
    const sourceId = asString(item.source_id);
    const title = asString(item.title);
    const url = asString(item.url);
    if (!sourceId || !title || !url) {
      return [];
    }
    return [
      {
        source_id: sourceId,
        title,
        url,
        snippet: asString(item.snippet),
        providers: asStringArray(item.providers),
        acquisition_method: asOptionalString(item.acquisition_method),
        cited_in_sections: asStringArray(item.cited_in_sections),
        occurrence_count: asNumber(item.occurrence_count),
        relevance_score: asOptionalNumber(item.relevance_score),
        confidence: asOptionalNumber(item.confidence),
      },
    ];
  });
}

function asSourceCards(value: unknown): SourceCard[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }
    const sourceId = asString(item.source_id);
    const title = asString(item.title);
    const url = asString(item.url);
    if (!sourceId || !title || !url) {
      return [];
    }
    return [
      {
        source_id: sourceId,
        title,
        url,
        snippet: asString(item.snippet),
        providers: asStringArray(item.providers),
        acquisition_method: asOptionalString(item.acquisition_method),
        fetched_at: asString(item.fetched_at),
        is_cited: Boolean(item.is_cited),
      },
    ];
  });
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function asOptionalString(value: unknown): string | undefined {
  const text = asString(value);
  return text || undefined;
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.filter((item): item is string => typeof item === "string");
}

function asNumber(value: unknown): number {
  return typeof value === "number" ? value : 0;
}

function asOptionalNumber(value: unknown): number | undefined {
  return typeof value === "number" ? value : undefined;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
