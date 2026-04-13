import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { RunSummaryTable } from "./RunSummaryTable";
import type { ResearchRunSummary } from "../types/research";

const runs: ResearchRunSummary[] = [
  {
    run_id: "run-1",
    status: "running",
    request: {
      question: "问题一",
      output_language: "zh-CN",
      max_iterations: 2,
      max_parallel_tasks: 3,
    },
    error_message: null,
    created_at: "2026-04-13T08:00:00+00:00",
    updated_at: "2026-04-13T08:10:00+00:00",
    completed_at: null,
  },
  {
    run_id: "run-2",
    status: "completed",
    request: {
      question: "问题二",
      output_language: "en",
      max_iterations: 3,
      max_parallel_tasks: 2,
    },
    error_message: null,
    created_at: "2026-04-13T09:00:00+00:00",
    updated_at: "2026-04-13T09:15:00+00:00",
    completed_at: "2026-04-13T09:15:00+00:00",
  },
];

describe("RunSummaryTable", () => {
  it("marks the active run in sidebar mode", () => {
    render(
      <MemoryRouter
        initialEntries={["/runs/run-2"]}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <RunSummaryTable runs={runs} emptyText="暂无研究记录。" variant="sidebar" />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: /问题二/ })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("已完成")).toBeInTheDocument();
  });

  it("renders empty state when there are no runs", () => {
    render(
      <MemoryRouter initialEntries={["/runs"]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <RunSummaryTable runs={[]} emptyText="还没有 run 记录。" />
      </MemoryRouter>,
    );

    expect(screen.getByText("还没有 run 记录。")).toBeInTheDocument();
  });
});
