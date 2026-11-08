import type { Register } from 'claude-code'

// The skill's bundled guides, inside the installed plugin's own folder.
const REFERENCES = ['skills', 'arlis-research', 'references']

const parts = (path: string) => path.replaceAll('\\', '/').split('/')

/** True for a file under REFERENCES in this plugin's folder, and nothing else. */
export function isBundledReference(root: string, filePath: unknown): boolean {
  if (typeof filePath !== 'string') return false
  const base = [...parts(root).filter((p, i) => p !== '' || i === 0), ...REFERENCES]
  const file = parts(filePath)
  if (file.length <= base.length) return false
  if (base.some((p, i) => file[i] !== p)) return false
  return file.slice(base.length).every((p) => p !== '' && p !== '.' && p !== '..')
}

export const register: Register = (on) => {
  on('tool.check', { tool: 'Read' }, async ($, e, next) => {
    const verdict = await next(e)
    // Only the default ask for a file outside the working directories.
    // An ask from a permission rule, a hook, a setting or another plugin stands.
    if (verdict.decision !== 'ask' || verdict.rule || verdict.hook || verdict.setting || verdict.plugin) {
      return verdict
    }
    const input = e.input as { file_path?: unknown } | undefined
    if (!isBundledReference($.plugin.root, input?.file_path)) return verdict
    return { decision: 'allow', reason: 'ArmLaw bundled reference' }
  })
}
