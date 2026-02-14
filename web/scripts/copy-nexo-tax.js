import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const srcDir = path.resolve(__dirname, '../..', 'nexo_tax')
const destDir = path.resolve(__dirname, '../dist', 'nexo_tax')

const copyDir = (src, dest) => {
  fs.mkdirSync(dest, { recursive: true })
  for (const file of fs.readdirSync(src)) {
    if (file === '__pycache__' || file === '.pytest_cache') continue
    const srcPath = path.join(src, file)
    const destPath = path.join(dest, file)
    const stat = fs.statSync(srcPath)
    if (stat.isDirectory()) {
      copyDir(srcPath, destPath)
    } else {
      fs.copyFileSync(srcPath, destPath)
    }
  }
}

if (fs.existsSync(srcDir)) {
  copyDir(srcDir, destDir)
  console.log('✓ Copied nexo_tax package to dist')
} else {
  console.warn('⚠ nexo_tax directory not found')
}
