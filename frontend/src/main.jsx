import { createRoot } from 'react-dom/client'
import { BrowserRouter, Route, Routes } from 'react-router'
import '@fontsource-variable/atkinson-hyperlegible-next/wght.css'
import '@fontsource-variable/bricolage-grotesque/wght.css'
import './styles.css'
import { Layout } from './Layout'
import { Home, KeyboardGuide, InstallGuide, NotFound } from './pages'
import { QuickPhrases, SignToVoice, TwoWay, VoiceToSign } from './screens'

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(error => {
      console.warn('Offline setup failed.', error)
    })
  })
}

createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="isaretten-sese" element={<SignToVoice />} />
        <Route path="sesten-isarete" element={<VoiceToSign />} />
        <Route path="iki-yonlu" element={<TwoWay />} />
        <Route path="hizli-ifadeler" element={<QuickPhrases />} />
        <Route path="klavye" element={<KeyboardGuide />} />
        <Route path="kurulum" element={<InstallGuide />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  </BrowserRouter>,
)
