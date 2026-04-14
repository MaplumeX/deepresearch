import { useState, useRef, useEffect } from 'react'
import { ArrowUp } from 'lucide-react'
import { Button } from './ui/button'
import { useChatStore } from '@/store/useChatStore'

export function ChatInput() {
  const [val, setVal] = useState('')
  const { sendMessage, isGenerating } = useChatStore()
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSend = () => {
    if (!val.trim() || isGenerating) return
    sendMessage(val.trim())
    setVal('')
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px'
    }
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
      textareaRef.current.style.height = Math.min(scrollHeight, 200) + 'px'
    }
  }

  useEffect(() => {
    if (!isGenerating && textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [isGenerating])

  return (
    <div className="absolute bottom-0 left-0 w-full bg-gradient-to-t from-background via-background/95 to-transparent pb-6 pt-16 px-4 md:px-0 pointer-events-none">
      <div className="max-w-3xl mx-auto relative group pointer-events-auto">
        <div className="absolute -inset-[2px] bg-gradient-to-r from-primary/10 via-primary/5 to-transparent rounded-3xl blur-md opacity-0 group-focus-within:opacity-100 transition-opacity duration-700"></div>
        <div className="relative flex items-end w-full bg-card border border-border shadow-[0_0_15px_rgba(0,0,0,0.03)] dark:shadow-[0_0_15px_rgba(0,0,0,0.2)] rounded-3xl overflow-hidden focus-within:ring-1 focus-within:ring-ring focus-within:border-ring transition-all duration-300">
          <textarea
            ref={textareaRef}
            value={val}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            disabled={isGenerating}
            placeholder="Message Deep Research..."
            className="w-full max-h-[200px] min-h-[56px] resize-none bg-transparent px-5 py-4 text-[15px] outline-none placeholder:text-muted-foreground leading-relaxed custom-scrollbar disabled:opacity-50 transition-colors"
            rows={1}
          />
          <div className="p-2 shrink-0">
            <Button 
              onClick={handleSend}
              disabled={!val.trim() || isGenerating}
              size="icon" 
              className="h-10 w-10 rounded-full bg-primary hover:bg-primary/90 transition-all duration-200 active:scale-95 shadow-sm disabled:opacity-50"
            >
              <ArrowUp className="h-5 w-5" />
            </Button>
          </div>
        </div>
        <div className="text-center mt-3 text-[11px] text-muted-foreground/60 w-full px-4 font-medium transition-colors hover:text-muted-foreground/80 cursor-default select-none pointer-events-auto">
          AI may produce inaccurate information.
        </div>
      </div>
    </div>
  )
}
