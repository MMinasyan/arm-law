import { expect, test } from 'claude-code/testing'
import { isBundledReference } from './allow-references.ts'

const ask = { decision: 'ask' } as const

// The plugin's folder, the one holding .claude-plugin/plugin.json.
const ROOT = new URL('..', import.meta.url).pathname.replace(/\/$/, '')

// The hooks registered here stand for the engine beneath the plugin.
async function check($: any, on: any, file_path: string, beneath: object = ask) {
  on('tool.check', () => beneath)
  return $.tool.check({ tool: 'Read', input: { file_path } })
}

const ref = (root: string, name = 'regulatory-legal-acts.md') =>
  `${root}/skills/arlis-research/references/${name}`

test('allows a bundled reference that would otherwise ask', async ($, on) => {
  const verdict = await check($, on, ref(ROOT))
  expect(verdict.decision).toBe('allow')
})

test('leaves other files in the plugin folder to Claude Code', async ($, on) => {
  const verdict = await check($, on, `${ROOT}/skills/arlis-research/SKILL.md`)
  expect(verdict.decision).toBe('ask')
})

test('leaves a path that climbs out of references', async ($, on) => {
  const verdict = await check($, on, ref(ROOT, '../../../../../etc/passwd'))
  expect(verdict.decision).toBe('ask')
})

test('leaves a look-alike directory', async ($, on) => {
  const verdict = await check($, on, `${ROOT}-evil/skills/arlis-research/references/x.md`)
  expect(verdict.decision).toBe('ask')
})

test('keeps a deny', async ($, on) => {
  const verdict = await check($, on, ref(ROOT), { decision: 'deny', rule: 'Read(**)' })
  expect(verdict.decision).toBe('deny')
})

test('keeps an ask from a permission rule', async ($, on) => {
  const verdict = await check($, on, ref(ROOT), { decision: 'ask', rule: 'Read(**)' })
  expect(verdict.decision).toBe('ask')
})

test('keeps an ask from a settings hook', async ($, on) => {
  const verdict = await check($, on, ref(ROOT), { decision: 'ask', hook: 'PreToolUse' })
  expect(verdict.decision).toBe('ask')
})

test('does not touch other tools', async ($, on) => {
  on('tool.check', () => ask)
  const verdict = await $.tool.check({ tool: 'Write', input: { file_path: ref(ROOT), content: '' } })
  expect(verdict.decision).toBe('ask')
})

test('path matching', () => {
  const root = '/home/u/.claude/plugins/cache/arm-law/arm-law/1.1.2'
  expect(isBundledReference(root, ref(root))).toBe(true)
  expect(isBundledReference(root + '/', ref(root))).toBe(true)
  expect(isBundledReference('C:\\p\\arm-law', 'C:\\p\\arm-law\\skills\\arlis-research\\references\\a.md')).toBe(true)
  expect(isBundledReference(root, `${root}/skills/arlis-research/references`)).toBe(false)
  expect(isBundledReference(root, `${root}/skills/arlis-research/references/`)).toBe(false)
  expect(isBundledReference(root, `${root}/skills/arlis-research/references/./a.md`)).toBe(false)
  expect(isBundledReference(root, 'skills/arlis-research/references/a.md')).toBe(false)
  expect(isBundledReference(root, 42)).toBe(false)
})
