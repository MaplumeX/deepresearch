import { MainLayout } from './layouts/MainLayout'
import { ChatArea } from './components/ChatArea'
import { ChatInput } from './components/ChatInput'

function App() {
  return (
    <MainLayout>
      <ChatArea />
      <ChatInput />
    </MainLayout>
  )
}

export default App
