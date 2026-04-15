import type { RunResult, StructuredReport } from '@/types/research'

function isStructuredReport(value: RunResult['final_structured_report']): value is StructuredReport {
  return Boolean(value)
    && typeof value.title === 'string'
    && typeof value.summary === 'string'
    && typeof value.markdown === 'string'
    && Array.isArray(value.sections)
    && Array.isArray(value.cited_source_ids)
    && Array.isArray(value.citation_index)
    && Array.isArray(value.source_cards)
}

export function getStructuredReport(result: RunResult | null | undefined): StructuredReport | null {
  if (isStructuredReport(result?.final_structured_report)) {
    return result.final_structured_report
  }
  if (isStructuredReport(result?.draft_structured_report)) {
    return result.draft_structured_report
  }
  return null
}
