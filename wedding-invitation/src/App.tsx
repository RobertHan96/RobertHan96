import { Couple } from './components/Couple'
import { Gallery } from './components/Gallery'
import { Hero } from './components/Hero'
import { Invitation } from './components/Invitation'
import { Location } from './components/Location'
import { PendingDetails } from './components/PendingDetails'
import { Footer, Share } from './components/Share'
import { WeddingDay } from './components/WeddingDay'
import { wedding } from './config/wedding'

function App() {
  useEffect(() => {
    const sections = document.querySelectorAll<HTMLElement>('.reveal-section')

    if (!('IntersectionObserver' in window)) {
      sections.forEach((section) => section.classList.add('is-visible'))
      return
    }

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return
        entry.target.classList.add('is-visible')
        observer.unobserve(entry.target)
      })
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 })

    sections.forEach((section) => observer.observe(section))
    return () => observer.disconnect()
  }, [])

  return (
    <main className="invitation-shell">
      <Hero wedding={wedding} />
      <Invitation invitation={wedding.invitation} />
      <Couple wedding={wedding} />
      <Gallery gallery={wedding.gallery} />
      <WeddingDay />
      <Location />
      <PendingDetails />
      <Share />
      <Footer />
    </main>
  )
}

export default App
import { useEffect } from 'react'
