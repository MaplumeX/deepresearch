import { formatStatus } from "../lib/format";
import type { RunStatus } from "../types/research";

interface StatusPillProps {
  status: RunStatus;
}

export function StatusPill({ status }: StatusPillProps) {
  return <span className={`status-pill status-pill-${status}`}>{formatStatus(status)}</span>;
}
