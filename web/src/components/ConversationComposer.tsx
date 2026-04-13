import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import type { ConversationTurnRequest, RunRequest } from "../types/research";


const composerSchema = z.object({
  question: z.string().trim().min(1, "请输入研究问题"),
  scope: z.string().trim().optional(),
  output_language: z.enum(["zh-CN", "en"]),
  max_iterations: z.coerce.number().int().min(1).max(5),
  max_parallel_tasks: z.coerce.number().int().min(1).max(5),
});

type ComposerValues = z.infer<typeof composerSchema>;

interface ConversationComposerProps {
  isSubmitting: boolean;
  onSubmit: (payload: ConversationTurnRequest) => void;
  submitLabel: string;
  placeholder?: string;
  parentRunId?: string;
  initialRequest?: Partial<RunRequest>;
  defaultSettingsOpen?: boolean;
}

const defaultValues: ComposerValues = {
  question: "",
  scope: "",
  output_language: "zh-CN",
  max_iterations: 2,
  max_parallel_tasks: 3,
};

export function ConversationComposer({
  isSubmitting,
  onSubmit,
  submitLabel,
  placeholder,
  parentRunId,
  initialRequest,
  defaultSettingsOpen = false,
}: ConversationComposerProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ComposerValues>({
    resolver: zodResolver(composerSchema),
    defaultValues: mergeInitialValues(initialRequest),
  });

  useEffect(() => {
    reset(mergeInitialValues(initialRequest));
  }, [initialRequest, reset]);

  return (
    <form
      className="conversation-composer"
      onSubmit={handleSubmit((values) => onSubmit(normalizePayload(values, parentRunId)))}
    >
      <label className="composer-main-field">
        <textarea
          {...register("question")}
          className="composer-textarea"
          rows={4}
          placeholder={placeholder ?? "输入问题，开始新的研究"}
        />
        {errors.question ? <small className="field-error">{errors.question.message}</small> : null}
      </label>

      <details className="composer-settings" open={defaultSettingsOpen}>
        <summary>研究设置</summary>
        <div className="composer-settings-grid">
          <label className="field">
            <span>研究范围</span>
            <textarea rows={3} {...register("scope")} placeholder="可选：限定来源、排除项或输出边界" />
            {errors.scope ? <small className="field-error">{errors.scope.message}</small> : null}
          </label>
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
      </details>

      <div className="composer-footer">
        <button className="primary-button" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "正在提交..." : submitLabel}
        </button>
      </div>
    </form>
  );
}

function mergeInitialValues(initialRequest?: Partial<RunRequest>): ComposerValues {
  return {
    ...defaultValues,
    ...initialRequest,
    scope: initialRequest?.scope ?? "",
  };
}

function normalizePayload(values: ComposerValues, parentRunId?: string): ConversationTurnRequest {
  return {
    ...values,
    parent_run_id: parentRunId,
    scope: values.scope?.trim() ? values.scope.trim() : undefined,
  };
}
