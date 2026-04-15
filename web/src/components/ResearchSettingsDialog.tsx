import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { Button } from './ui/button'
import type { ResearchSettings, OutputLanguage } from '@/store/useSettingsStore'

interface ResearchSettingsDialogProps {
  open: boolean
  title?: string
  confirmLabel?: string
  initialValues: ResearchSettings
  onClose: () => void
  onConfirm: (values: ResearchSettings) => void
}

export function ResearchSettingsDialog({
  open,
  title = '研究设置',
  confirmLabel = '保存',
  initialValues,
  onClose,
  onConfirm,
}: ResearchSettingsDialogProps) {
  const [draft, setDraft] = useState<ResearchSettings>(initialValues)

  useEffect(() => {
    if (open) {
      setDraft(initialValues)
    }
  }, [open, initialValues])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-border bg-background p-5 shadow-2xl">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-1.5 text-muted-foreground transition-colors hover:bg-muted"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mt-5 space-y-4">
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">输出语言</label>
            <select
              value={draft.outputLanguage}
              onChange={(e) => setDraft((d) => ({ ...d, outputLanguage: e.target.value as OutputLanguage }))}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            >
              <option value="zh-CN">简体中文</option>
              <option value="en">English</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">最大迭代次数（1-5）</label>
            <input
              type="number"
              min={1}
              max={5}
              value={draft.maxIterations}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10)
                setDraft((d) => ({ ...d, maxIterations: Number.isNaN(val) ? d.maxIterations : Math.max(1, Math.min(5, val)) }))
              }}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground">数值越高研究越深入，但耗时更长。</p>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-foreground">最大并行任务（1-5）</label>
            <input
              type="number"
              min={1}
              max={5}
              value={draft.maxParallelTasks}
              onChange={(e) => {
                const val = parseInt(e.target.value, 10)
                setDraft((d) => ({ ...d, maxParallelTasks: Number.isNaN(val) ? d.maxParallelTasks : Math.max(1, Math.min(5, val)) }))
              }}
              className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring"
            />
            <p className="text-xs text-muted-foreground">每轮迭代同时搜索的方向数量。</p>
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            取消
          </Button>
          <Button onClick={() => onConfirm(draft)}>{confirmLabel}</Button>
        </div>
      </div>
    </div>
  )
}
