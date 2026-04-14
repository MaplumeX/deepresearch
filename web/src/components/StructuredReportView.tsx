import ReactMarkdown from "react-markdown";

import { linkifyCitations } from "../lib/report";
import type { StructuredReport } from "../types/research";


interface StructuredReportViewProps {
  report: StructuredReport;
}

export function StructuredReportView({ report }: StructuredReportViewProps) {
  return (
    <div className="structured-report">
      <div className="structured-report-meta">
        <span>{report.sections.length} 个章节</span>
        <span>{report.cited_source_ids.length} 个已引用来源</span>
        <span>{report.source_cards.length} 个来源卡片</span>
      </div>

      {report.summary ? (
        <section className="report-section report-section-summary">
          <div className="report-section-header">
            <h3>执行摘要</h3>
          </div>
          <MarkdownBlock markdown={report.summary} />
        </section>
      ) : null}

      {report.sections
        .filter((section) => section.heading !== "Executive Summary")
        .map((section) => (
          <section key={section.section_id} className="report-section" id={`section-${section.section_id}`}>
            <div className="report-section-header">
              <h3>{section.heading}</h3>
              {section.cited_source_ids.length > 0 ? (
                <span className="report-section-citations">{section.cited_source_ids.join(" · ")}</span>
              ) : (
                <span className="report-section-citations report-section-citations-muted">无证据引用</span>
              )}
            </div>
            <MarkdownBlock markdown={section.body_markdown} />
          </section>
        ))}

      <section className="report-sources">
        <div className="report-section-header">
          <h3>来源索引</h3>
          <span className="report-section-citations">
            {report.citation_index.length > 0 ? "按引用优先排序" : "当前没有可展示的引用索引"}
          </span>
        </div>
        <div className="source-card-grid">
          {report.source_cards.map((card) => (
            <article key={card.source_id} className="source-card" id={`source-${card.source_id}`}>
              <div className="source-card-header">
                <a href={card.url} target="_blank" rel="noreferrer">
                  {card.title}
                </a>
                <span className={card.is_cited ? "source-status source-status-cited" : "source-status"}>
                  {card.is_cited ? "已引用" : "未引用"}
                </span>
              </div>
              <p className="source-card-meta">
                <span>{card.source_id}</span>
                {card.providers.length > 0 ? <span>{card.providers.join(" / ")}</span> : null}
                {card.acquisition_method ? <span>{card.acquisition_method}</span> : null}
              </p>
              {card.snippet ? <p className="source-card-snippet">{card.snippet}</p> : null}
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}

function MarkdownBlock({ markdown }: { markdown: string }) {
  return (
    <div className="report-markdown">
      <ReactMarkdown
        components={{
          a: ({ href, children }) => {
            if (href?.startsWith("#source-")) {
              return (
                <a href={href} className="citation-link">
                  {children}
                </a>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" className="report-link">
                {children}
              </a>
            );
          },
        }}
      >
        {linkifyCitations(markdown)}
      </ReactMarkdown>
    </div>
  );
}
