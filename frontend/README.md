# SignBridge-TR frontend

SB-54 introduces a Turkish-language PWA shell for the project’s TİD ↔ Turkish interface. We chose **React with Vite** because this milestone needs client-side routing, reusable components and a static build that runs independently of the backend. There is no server-rendering or server-side data requirement to justify Next.js here. No API keys, environment file or backend process are needed. Icons and fonts ship with the app.

## Run locally

Use Node.js 22.12 or newer with npm. From the repository root:

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

Open <http://127.0.0.1:5173/>. On Windows with PowerShell script execution disabled, use `npm.cmd` for `npm`. Press Ctrl+C to stop the server.

## Build and preview

From `frontend/`, run:

```sh
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open <http://127.0.0.1:4173/>. The build writes the app and a versioned service worker to `dist/`. Only the production build registers the worker. After a first successful online installation of the worker, it serves the shell, icons and fonts offline. For hosting, serve `dist/` at the origin root over HTTPS and rewrite application routes to `index.html` on direct navigation. Local preview handles that rewrite.

## Add a screen

Register a child route under `Layout` in [src/main.jsx](src/main.jsx). Each screen renders one descriptive `h1` with `tabIndex={-1}`. The [shared layout](src/Layout.jsx) supplies the skip link, navigation, main landmark and footer. On a pathname change it sets the document title from the heading and moves focus there, including on browser Back and Forward. Initial loading leaves the skip link first in the tab order.

The current routes are `/`, `/klavye` and `/kurulum`, with a recovery link for unknown paths. SB-54 covers MF1’s PWA launch foundation and MF12’s shared navigation and reading experience. Mode selection and two-way conversation belong to SB-55.

## Verify in the production preview

| Action | Expected result |
| --- | --- |
| Open the home page in a fresh tab. Press Tab, Enter, then Tab. | “Ana içeriğe geç” appears first. Enter focuses the main content. The next Tab reaches “Klavye ile gezinme”. |
| Open that link with Enter, then use Back and Forward. | The new page title updates and a visible outline surrounds its main heading each time. On the keyboard guide, the next Tab reaches “Başlangıca dön”. |
| Inspect the home, keyboard, install and unknown routes at 360, 768 and 1280 CSS pixels. | Text wraps, all links stay visible and the page has no horizontal scroll. |
| With VoiceOver or TalkBack, navigate by headings, landmarks and links. Open the keyboard guide. | The navigation has a name, links describe their destination, and the new heading is announced. |
| In a regular supported browser, install the preview and open its icon. After the service worker is active, disconnect the network and reload a guide. | The icon launches the home route in a standalone window. The guide, fonts and navigation remain available offline. |

During SB-54 verification, local Edge exercised keyboard navigation, direct routes, unknown paths and offline reload. The accessibility tree exposed the labelled navigation, headings and links. axe reported zero violations on all four views at the three widths above. The regular-profile installability check passed. Physical-device installation and spoken screen-reader output remain manual checks. These results cover this shell only and do not establish WCAG conformance.
