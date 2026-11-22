import { useLayoutEffect, useRef } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'

export function Layout() {
  const { pathname } = useLocation()
  const previousPath = useRef(pathname)
  const main = useRef(null)

  useLayoutEffect(() => {
    const heading = main.current.querySelector('h1')
    document.title = heading.textContent + ' · SignBridge-TR'
    if (previousPath.current !== pathname) {
      heading.focus()
      window.scrollTo(0, 0)
    }
    previousPath.current = pathname
  }, [pathname])

  return (
    <>
      <a className="skip-link" href="#icerik" onClick={event => {
        // Keep the skip target out of history so Back restores the route heading.
        event.preventDefault()
        main.current.focus()
      }}>Skip to main content</a>
      <header className="masthead">
        <div className="wrap header-inner">
          <span className="wordmark"><img src="/icon-192.png" alt="" />SignBridge</span>
          <nav aria-label="Main navigation">
            <NavLink to="/" end>Home</NavLink>
            <NavLink to="/klavye">Keyboard</NavLink>
            <NavLink to="/kurulum">Install</NavLink>
          </nav>
        </div>
      </header>
      <main id="icerik" ref={main} tabIndex={-1} className="wrap">
        <Outlet />
      </main>
      <footer className="wrap footer"><span>SignBridge-TR</span>Yaşar University</footer>
    </>
  )
}
