import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import OpsApp from './ops/OpsApp.tsx'

const path = window.location.pathname
const isOps = path === '/ops' || path.startsWith('/ops/')

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {isOps ? <OpsApp /> : <App />}
  </StrictMode>,
)
