import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import App from '@/App.vue'

vi.mock('@/api.js', () => ({ fetchRecipes: vi.fn() }))

global.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
)

describe('App support link', () => {
  it('renders a support link with the correct href, target, rel, and text', async () => {
    const wrapper = mount(App, { attachTo: document.body })
    const link = wrapper.find('a.support-link')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('Support this project')
    expect(link.attributes('href')).toBe('https://github.com/sponsors/ConnorGriffin')
    expect(link.attributes('target')).toBe('_blank')
    const rel = link.attributes('rel')
    expect(rel).toContain('noopener')
    expect(rel).toContain('noreferrer')
    expect(link.attributes('aria-label')).toContain('GitHub Sponsors')
    wrapper.unmount()
  })
})
