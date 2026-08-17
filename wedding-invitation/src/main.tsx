import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { GuestSnapAdmin } from './components/GuestSnapAdmin.tsx'

const page = window.location.pathname === '/guest-snap-admin' ? <GuestSnapAdmin /> : <App />

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {page}
  </StrictMode>,
)
