import { FormEvent, useEffect, useState } from "react";

interface ReviewPanelProps {
  draftReport: string;
  isSubmitting: boolean;
  onSubmit: (editedReport?: string) => void;
}

export function ReviewPanel({ draftReport, isSubmitting, onSubmit }: ReviewPanelProps) {
  const [editedReport, setEditedReport] = useState(draftReport);

  useEffect(() => {
    setEditedReport(draftReport);
  }, [draftReport]);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalized = editedReport.trim();
    onSubmit(normalized === draftReport.trim() ? undefined : normalized);
  };

  return (
    <form className="panel review-panel" onSubmit={handleSubmit}>
      <div className="section-header">
        <h2>人工审核</h2>
        <p>当前 run 已暂停。你可以直接继续，也可以编辑草稿后继续执行。</p>
      </div>
      <label className="field">
        <span>草稿报告</span>
        <textarea rows={14} value={editedReport} onChange={(event) => setEditedReport(event.target.value)} />
      </label>
      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在提交..." : "提交审核并继续"}
        </button>
      </div>
    </form>
  );
}
