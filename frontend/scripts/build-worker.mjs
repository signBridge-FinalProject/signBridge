import { createHash } from 'node:crypto'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const output = new URL('../dist/', import.meta.url)
const worker = await readFile(new URL('./worker.js', import.meta.url), 'utf8')
const entries = await readdir(output, { recursive: true, withFileTypes: true })
const assets = entries
  .filter(entry => entry.isFile() && entry.name !== 'sw.js')
  .map(entry => path.relative(fileURLToPath(output), path.join(entry.parentPath, entry.name)))

// Include the file contents so changes to unversioned icons and HTML rotate the cache too.
const hash = createHash('sha256').update(worker)
const urls = []
for (const asset of assets.sort()) {
  const url = asset.split(path.sep).join('/')
  hash.update(url).update(await readFile(new URL(url, output)))
  urls.push('/' + url)
}
const name = 'signbridge-shell-' + hash.digest('hex').slice(0, 16)
const config = 'const cacheName = ' + JSON.stringify(name) + '\nconst assets = ' + JSON.stringify(urls)
await writeFile(new URL('sw.js', output), config + '\n' + worker)
