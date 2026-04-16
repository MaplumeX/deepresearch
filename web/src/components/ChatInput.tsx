import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Sparkles, Settings2 } from 'lucide-react'
import { Button } from './ui/button'
import { useChatStore } from '@/store/useChatStore'
import { useSettingsStore, type ResearchSettings } from '@/store/useSettingsStore'
import { ResearchSettingsDialog } from './ResearchSettingsDialog'
import { cn } from '@/lib/utils'

function ResearchExitDialog({
  open,
  busy,
  onCancel,
  onConfirm,
}: {
  open: boolean
  busy: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="w-full max-w-md rounded-3xl border border-border bg-background p-6 shadow-2xl">
        <h2 className="text-lg font-semibold">退出 Deep Research？</h2>
        <p className="mt-3 text-sm leading-6 text-muted-foreground">
          {busy
            ? '当前研究仍在进行中。离开后任务会继续，你可以稍后从侧边栏回来查看结果。确认后将返回新会话界面，后续消息默认按普通对话发送。'
            : '当前研究会话会保留在侧边栏。确认后将返回新会话界面，后续消息默认按普通对话发送。'}
        </p>
        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel}>
            取消
          </Button>
          <Button onClick={onConfirm}>
            返回新对话
          </Button>
        </div>
      </div>
    </div>
  )
}

export function ChatInput() {
  const [val, setVal] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [settingsDialogOpen, setSettingsDialogOpen] = useState(false)
  const [sessionSettings, setSessionSettings] = useState<Partial<ResearchSettings> | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const {
    sendMessage,
    isGenerating,
    draftMode,
    activeConversation,
    activateResearchDraft,
    deactivateResearchDraft,
    exitResearchConversation,
  } = useChatStore()
  const globalSettings = useSettingsStore()

  const isResearchConversation = activeConversation?.mode === 'research'
  const showResearchButton = !activeConversation || isResearchConversation
  const researchSelected = isResearchConversation || (!activeConversation && draftMode === 'research')
  const researchBusy = activeConversation?.latest_run_status === 'queued' || activeConversation?.latest_run_status === 'running'
  const placeholder = researchSelected ? 'Ask Deep Research...' : 'Message...'
  const dialogVisible = dialogOpen && isResearchConversation

  const resolvedSettings: ResearchSettings = {
    outputLanguage: sessionSettings?.outputLanguage ?? globalSettings.outputLanguage,
    maxIterations: sessionSettings?.maxIterations ?? globalSettings.maxIterations,
    maxParallelTasks: sessionSettings?.maxParallelTasks ?? globalSettings.maxParallelTasks,
  }

  const handleSend = () => {
    if (!val.trim() || isGenerating) {
      return
    }
    void sendMessage(val.trim(), sessionSettings ?? undefined)
    setVal('')
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px'
    }
  }

  const handleResearchClick = () => {
    if (isResearchConversation) {
      setDialogOpen(true)
      return
    }
    if (draftMode === 'research') {
      deactivateResearchDraft()
      setSessionSettings(null)
      return
    }
    activateResearchDraft()
  }

  const handleConfirmExitResearch = () => {
    setDialogOpen(false)
    exitResearchConversation()
    setSessionSettings(null)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setVal(e.target.value)
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px'
      const scrollHeight = textareaRef.current.scrollHeight
      textareaRef.current.style.height = `${Math.min(scrollHeight, 200)}px`
    }
  }

  useEffect(() => {
    if (!isGenerating && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isGenerating])

  return (
    <>
      <ResearchExitDialog
        open={dialogVisible}
        busy={researchBusy}
        onCancel={() => setDialogOpen(false)}
        onConfirm={handleConfirmExitResearch}
      />

      <ResearchSettingsDialog
        key={settingsDialogOpen ? 'open' : 'closed'}
        open={settingsDialogOpen}
        title="本次研究配置"
        confirmLabel="应用"
        initialValues={resolvedSettings}
        onClose={() => setSettingsDialogOpen(false)}
        onConfirm={(next) => {
          setSessionSettings(next)
          setSettingsDialogOpen(false)
        }}
      />

      <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-background via-background/95 to-transparent pb-6 pt-16 px-4 md:px-0 pointer-events-none">
        <div className="max-w-3xl mx-auto relative group pointer-events-auto">
          <div className="absolute -inset-[2px] bg-gradient-to-r from-primary/10 via-primary/5 to-transparent rounded-[2rem] blur-md opacity-0 group-focus-within:opacity-100 transition-opacity duration-500"></div>
          <div className="relative overflow-hidden rounded-[2rem] border border-border bg-card shadow-[0_2px_20px_rgba(0,0,0,0.03)] transition-all duration-300 focus-within:border-ring focus-within:ring-1 focus-within:ring-ring dark:shadow-[0_2px_20px_rgba(0,0,0,0.2)]">
            <textarea
              ref={textareaRef}
              value={val}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              disabled={isGenerating}
              placeholder={placeholder}
              className="w-full max-h-[200px] min-h-[56px] resize-none bg-transparent px-5 pt-4 pb-2 text-[15px] leading-relaxed outline-none placeholder:text-muted-foreground transition-colors custom-scrollbar disabled:opacity-50"
              rows={1}
            />
            <div className="flex items-center justify-between px-4 pb-3 pt-1">
              <div className="flex items-center gap-2">
                {showResearchButton && (
                  <button
                    type="button"
                    onClick={handleResearchClick}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors',
                      researchSelected
                        ? 'border-transparent bg-primary text-primary-foreground hover:bg-primary/90'
                        : 'border-border bg-transparent text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <Sparkles className="h-3.5 w-3.5" />
                    Deep Research
                  </button>
                )}
                {researchSelected && !isResearchConversation && (
                  <button
                    type="button"
                    onClick={() => setSettingsDialogOpen(true)}
                    className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-border bg-transparent text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
                    aria-label="调整研究配置"
                  >
                    <Settings2 className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
              <Button
                onClick={handleSend}
                disabled={!val.trim() || isGenerating}
                size="icon"
                className="h-9 w-9 rounded-full bg-primary shadow-sm transition-all duration-200 hover:bg-primary/90 active:scale-95 disabled:opacity-50"
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <div className="mt-3 w-full px-4 text-center text-[11px] font-medium text-muted-foreground/50 transition-colors hover:text-muted-foreground/70 cursor-default select-none pointer-events-auto">
            Chat 为默认模式。只有启用 Deep Research 后，首条消息才会创建研究会话。
          </div>
        </div>
      </div>
    </>
  )
}
