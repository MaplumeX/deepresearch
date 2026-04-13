export function formatDateTime(value: string | null): string {
  if (!value) {
    return "—";
  }

  const date = new Date(value);
  return new Intl.DateTimeFormat("zh-CN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatStatus(status: string): string {
  const labels: Record<string, string> = {
    queued: "排队中",
    running: "执行中",
    interrupted: "待审核",
    completed: "已完成",
    failed: "失败",
  };
  return labels[status] ?? status;
}
