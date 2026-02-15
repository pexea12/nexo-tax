import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const srcDir = path.resolve(__dirname, '../..', 'nexo_tax')

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
  const distDir = path.resolve(__dirname, '../dist', 'nexo_tax')
  const publicDir = path.resolve(__dirname, '../public', 'nexo_tax')
  copyDir(srcDir, distDir)
  copyDir(srcDir, publicDir)
  console.log('✓ Copied nexo_tax package to dist and public')
} else {
  console.warn('⚠ nexo_tax directory not found')
}

// Copy sample CSV to public and dist
const sampleSrc = path.resolve(__dirname, '../../data/sample_nexo_export.csv')
if (fs.existsSync(sampleSrc)) {
  fs.copyFileSync(sampleSrc, path.resolve(__dirname, '../public/sample_nexo_export.csv'))
  fs.mkdirSync(path.resolve(__dirname, '../dist'), { recursive: true })
  fs.copyFileSync(sampleSrc, path.resolve(__dirname, '../dist/sample_nexo_export.csv'))
  console.log('✓ Copied sample_nexo_export.csv')
}
