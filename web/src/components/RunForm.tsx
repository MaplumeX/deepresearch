import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { RunRequest } from "../types/research";

const runSchema = z.object({
  question: z.string().trim().min(1, "请输入研究问题"),
  scope: z.string().trim().optional(),
  output_language: z.enum(["zh-CN", "en"]),
  max_iterations: z.coerce.number().int().min(1).max(5),
  max_parallel_tasks: z.coerce.number().int().min(1).max(5),
});

type RunFormValues = z.infer<typeof runSchema>;

interface RunFormProps {
  isSubmitting: boolean;
  onSubmit: (payload: RunRequest) => void;
}

const defaultValues: RunFormValues = {
  question: "",
  scope: "",
  output_language: "zh-CN",
  max_iterations: 2,
  max_parallel_tasks: 3,
};

export function RunForm({ isSubmitting, onSubmit }: RunFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RunFormValues>({
    resolver: zodResolver(runSchema),
    defaultValues,
  });

  return (
    <form className="panel form-panel" onSubmit={handleSubmit((values) => onSubmit(normalizePayload(values)))}>
      <div className="section-header">
        <h2>创建新研究</h2>
        <p>填写问题和预算参数，系统会异步创建 run，并在详情页通过 SSE 推送状态变化。</p>
      </div>

      <label className="field">
        <span>研究问题</span>
        <textarea
          rows={5}
          {...register("question")}
          placeholder="例如：比较 LangGraph deep research agent 的常见执行模型和恢复策略"
        />
        {errors.question ? <small>{errors.question.message}</small> : null}
      </label>

      <label className="field">
        <span>研究范围</span>
        <textarea rows={3} {...register("scope")} placeholder="可选：限定场景、来源偏好或语言边界" />
        {errors.scope ? <small>{errors.scope.message}</small> : null}
      </label>

      <div className="field-grid">
        <label className="field">
          <span>输出语言</span>
          <select {...register("output_language")}>
            <option value="zh-CN">中文</option>
            <option value="en">English</option>
          </select>
        </label>
        <label className="field">
          <span>最大迭代轮次</span>
          <input type="number" min={1} max={5} {...register("max_iterations")} />
        </label>
        <label className="field">
          <span>最大并行任务数</span>
          <input type="number" min={1} max={5} {...register("max_parallel_tasks")} />
        </label>
      </div>

      <div className="form-actions">
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在创建..." : "创建 run"}
        </button>
      </div>
    </form>
  );
}

function normalizePayload(values: RunFormValues): RunRequest {
  return {
    ...values,
    scope: values.scope?.trim() ? values.scope.trim() : undefined,
  };
}
