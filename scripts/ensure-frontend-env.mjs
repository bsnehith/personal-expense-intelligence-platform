/**
 * Ensures frontend/.env exists with VITE_API_BASE_URL for local dev.
 */
import { existsSync, writeFileSync, readFileSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const envPath = join(root, 'frontend', '.env')
const line = 'VITE_API_BASE_URL=http://localhost:8000\n'

if (!existsSync(envPath)) {
  writeFileSync(envPath, line, 'utf8')
  console.log('Created frontend/.env with VITE_API_BASE_URL=http://localhost:8000')
} else {
  const cur = readFileSync(envPath, 'utf8')
  if (!cur.includes('VITE_API_BASE_URL')) {
    writeFileSync(envPath, cur + (cur.endsWith('\n') ? '' : '\n') + line, 'utf8')
    console.log('Appended VITE_API_BASE_URL to frontend/.env')
  }
}
