import { ArrowLeft, ArrowUpRight, AudioLines, Hand, Keyboard, MonitorDown } from 'lucide-react'
import { Link } from 'react-router'

function GuideLink({ to, title, description, Icon }) {
  return (
    <Link to={to} className="guide-link">
      <span className="guide-icon"><Icon aria-hidden="true" /></span>
      <span><strong>{title}</strong><span className="detail">{description}</span></span>
      <ArrowUpRight className="arrow" aria-hidden="true" />
    </Link>
  )
}

export function Home() {
  return (
    <>
      <div className="hero">
        <div className="hero-copy">
          <h1 tabIndex={-1}>SignBridge</h1>
          <p>A research project exploring how Turkish Sign Language (TİD) users and Turkish speakers can communicate in everyday situations.</p>
        </div>
        <div className="illustration" aria-hidden="true">
          <div className="bubble sign"><Hand /></div>
          <div className="bubble voice"><AudioLines /></div>
        </div>
      </div>
      <section className="guide-section" aria-labelledby="rehber">
        <h2 id="rehber">User guides</h2>
        <div className="guide-list">
          <GuideLink to="/klavye" title="Keyboard navigation" description="Follow links and skip to the main content." Icon={Keyboard} />
          <GuideLink to="/kurulum" title="Install SignBridge" description="Open the app from your home screen and use it offline." Icon={MonitorDown} />
        </div>
      </section>
    </>
  )
}

function Article({ title, children }) {
  return (
    <article className="article">
      <h1 tabIndex={-1}>{title}</h1>
      {children}
      <Link className="back-link" to="/"><ArrowLeft aria-hidden="true" />Back to home</Link>
    </article>
  )
}

export function KeyboardGuide() {
  return (
    <Article title="Keyboard navigation">
      <h2>Move between links</h2>
      <p>Press <kbd>Tab</kbd> to move to the next link or <kbd>Shift</kbd> + <kbd>Tab</kbd> to move back. An outline shows which link has focus.</p>
      <p>Press <kbd>Enter</kbd> to open the link. Focus moves to the heading on the new page.</p>
      <h2>Skip the menu</h2>
      <p>When you first open a page, press <kbd>Tab</kbd> to reveal “Skip to main content”. Press <kbd>Enter</kbd> to go straight to the content.</p>
    </Article>
  )
}

export function InstallGuide() {
  return (
    <Article title="Install SignBridge">
      <h2>Add the app to your home screen</h2>
      <p>In a browser that supports installation, use the install icon in the address bar or the install option in the browser menu. In Safari on iPhone, open the Share menu and choose “Add to Home Screen”.</p>
      <p>Once installed, select the SignBridge icon on your device to open the app.</p>
      <h2>Use the app offline</h2>
      <p>Stay online the first time you open the app. Once your device has saved the app files, you can open the home page and both guides offline.</p>
    </Article>
  )
}

export function NotFound() {
  return <Article title="Page not found"><p>Check the address or return to the home page.</p></Article>
}
