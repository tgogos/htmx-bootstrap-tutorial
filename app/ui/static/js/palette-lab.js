/*!
 * Live Bootstrap token playground for this admin starter.
 * Edits set inline CSS variables on <html> (override palettes.css for the session).
 * Does not persist a new named palette — use Copy CSS to paste into palettes.css.
 */

(() => {
  'use strict'

  const root = document.documentElement

  /** Theme + surface tokens shown as pickers (curated, not every --bs-*). */
  const TOKENS = [
    {
      group: 'Theme colours',
      items: [
        { key: 'primary', css: '--bs-primary', rgb: '--bs-primary-rgb', derive: true },
        { key: 'secondary', css: '--bs-secondary', rgb: '--bs-secondary-rgb', derive: true },
        { key: 'success', css: '--bs-success', rgb: '--bs-success-rgb', derive: true },
        { key: 'danger', css: '--bs-danger', rgb: '--bs-danger-rgb', derive: true },
        { key: 'warning', css: '--bs-warning', rgb: '--bs-warning-rgb', derive: true },
        { key: 'info', css: '--bs-info', rgb: '--bs-info-rgb', derive: true }
      ]
    },
    {
      group: 'Surfaces & text',
      items: [
        { key: 'body-bg', css: '--bs-body-bg', rgb: '--bs-body-bg-rgb' },
        { key: 'body-color', css: '--bs-body-color', rgb: '--bs-body-color-rgb' },
        { key: 'secondary-bg', css: '--bs-secondary-bg', rgb: '--bs-secondary-bg-rgb' },
        { key: 'tertiary-bg', css: '--bs-tertiary-bg', rgb: '--bs-tertiary-bg-rgb' },
        { key: 'emphasis-color', css: '--bs-emphasis-color', rgb: '--bs-emphasis-color-rgb' },
        { key: 'border-color', css: '--bs-border-color' }
      ]
    },
    {
      group: 'Links & focus',
      items: [
        { key: 'link-color', css: '--bs-link-color', rgb: '--bs-link-color-rgb' },
        { key: 'link-hover-color', css: '--bs-link-hover-color', rgb: '--bs-link-hover-color-rgb' },
        { key: 'focus-ring', css: '--bs-focus-ring-color', kind: 'rgba' }
      ]
    }
  ]

  const flatTokens = TOKENS.flatMap(g => g.items)

  const clamp = (n, min, max) => Math.min(max, Math.max(min, n))

  const parseColor = value => {
    if (!value) {
      return null
    }
    const v = value.trim()
    const hex = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(v)
    if (hex) {
      let h = hex[1]
      if (h.length === 3) {
        h = h.split('').map(c => c + c).join('')
      }
      return {
        r: parseInt(h.slice(0, 2), 16),
        g: parseInt(h.slice(2, 4), 16),
        b: parseInt(h.slice(4, 6), 16),
        a: 1
      }
    }
    const rgb = /^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i.exec(v)
    if (rgb) {
      return {
        r: Number(rgb[1]),
        g: Number(rgb[2]),
        b: Number(rgb[3]),
        a: rgb[4] === undefined ? 1 : Number(rgb[4])
      }
    }
    return null
  }

  const toHex = ({ r, g, b }) => {
    const h = n => clamp(Math.round(n), 0, 255).toString(16).padStart(2, '0')
    return `#${h(r)}${h(g)}${h(b)}`
  }

  const toRgbList = ({ r, g, b }) =>
    `${clamp(Math.round(r), 0, 255)}, ${clamp(Math.round(g), 0, 255)}, ${clamp(Math.round(b), 0, 255)}`

  const mix = (a, b, t) => ({
    r: a.r + (b.r - a.r) * t,
    g: a.g + (b.g - a.g) * t,
    b: a.b + (b.b - a.b) * t,
    a: 1
  })

  const relativeLuminance = ({ r, g, b }) => {
    const lin = c => {
      const s = c / 255
      return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
    }
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  }

  const readComputed = cssVar =>
    getComputedStyle(root).getPropertyValue(cssVar).trim()

  const isDarkTheme = () => root.getAttribute('data-bs-theme') === 'dark'

  const deriveRelated = (name, rgb) => {
    const dark = isDarkTheme()
    const white = { r: 255, g: 255, b: 255, a: 1 }
    const black = { r: 0, g: 0, b: 0, a: 1 }
    if (dark) {
      return {
        [`--bs-${name}-text-emphasis`]: toHex(mix(rgb, white, 0.35)),
        [`--bs-${name}-bg-subtle`]: toHex(mix(rgb, black, 0.82)),
        [`--bs-${name}-border-subtle`]: toHex(mix(rgb, black, 0.45))
      }
    }
    return {
      [`--bs-${name}-text-emphasis`]: toHex(mix(rgb, black, 0.55)),
      [`--bs-${name}-bg-subtle`]: toHex(mix(rgb, white, 0.85)),
      [`--bs-${name}-border-subtle`]: toHex(mix(rgb, white, 0.45))
    }
  }

  const onPrimaryFor = rgb =>
    relativeLuminance(rgb) > 0.45 ? '#000' : '#fff'

  const deriveToggle = () => document.querySelector('#palette-lab-derive')

  const setToken = (token, hexOrRgba, { syncInputs = true } = {}) => {
    const parsed = parseColor(hexOrRgba)
    if (!parsed) {
      return
    }

    if (token.kind === 'rgba') {
      const rgba = `rgba(${toRgbList(parsed)}, ${parsed.a === 1 ? 0.25 : parsed.a})`
      root.style.setProperty(token.css, rgba)
      if (syncInputs) {
        const colorInput = document.querySelector(`[data-lab-color="${token.key}"]`)
        const textInput = document.querySelector(`[data-lab-text="${token.key}"]`)
        if (colorInput) {
          colorInput.value = toHex(parsed)
        }
        if (textInput) {
          textInput.value = rgba
        }
      }
      return
    }

    const hex = toHex(parsed)
    root.style.setProperty(token.css, hex)
    if (token.rgb) {
      root.style.setProperty(token.rgb, toRgbList(parsed))
    }

    if (token.key === 'primary') {
      root.style.setProperty('--bs-link-color', hex)
      root.style.setProperty('--bs-link-color-rgb', toRgbList(parsed))
      root.style.setProperty('--bs-focus-ring-color', `rgba(${toRgbList(parsed)}, 0.25)`)
      root.style.setProperty('--admin-on-primary', onPrimaryFor(parsed))
      const hover = mix(parsed, isDarkTheme() ? { r: 255, g: 255, b: 255, a: 1 } : { r: 0, g: 0, b: 0, a: 1 }, 0.2)
      root.style.setProperty('--bs-link-hover-color', toHex(hover))
      root.style.setProperty('--bs-link-hover-color-rgb', toRgbList(hover))
    }

    if (token.derive && deriveToggle()?.checked) {
      const related = deriveRelated(token.key, parsed)
      Object.entries(related).forEach(([prop, value]) => {
        root.style.setProperty(prop, value)
      })
      root.style.setProperty(`--admin-on-${token.key}`, onPrimaryFor(parsed))
    }

    if (syncInputs) {
      const colorInput = document.querySelector(`[data-lab-color="${token.key}"]`)
      const textInput = document.querySelector(`[data-lab-text="${token.key}"]`)
      if (colorInput) {
        colorInput.value = hex
      }
      if (textInput) {
        textInput.value = hex
      }
    }

    updateExport()
  }

  const clearOverrides = () => {
    flatTokens.forEach(token => {
      root.style.removeProperty(token.css)
      if (token.rgb) {
        root.style.removeProperty(token.rgb)
      }
    })
    ;[
      'primary', 'secondary', 'success', 'danger', 'warning', 'info'
    ].forEach(name => {
      root.style.removeProperty(`--bs-${name}-text-emphasis`)
      root.style.removeProperty(`--bs-${name}-bg-subtle`)
      root.style.removeProperty(`--bs-${name}-border-subtle`)
      root.style.removeProperty(`--admin-on-${name}`)
    })
    root.style.removeProperty('--bs-link-color')
    root.style.removeProperty('--bs-link-color-rgb')
    root.style.removeProperty('--bs-link-hover-color')
    root.style.removeProperty('--bs-link-hover-color-rgb')
    root.style.removeProperty('--bs-focus-ring-color')
    root.style.removeProperty('--admin-on-primary')
  }

  const syncInputsFromComputed = () => {
    flatTokens.forEach(token => {
      const raw = readComputed(token.css)
      const parsed = parseColor(raw)
      const colorInput = document.querySelector(`[data-lab-color="${token.key}"]`)
      const textInput = document.querySelector(`[data-lab-text="${token.key}"]`)
      if (!colorInput || !textInput) {
        return
      }
      if (token.kind === 'rgba' && parsed) {
        colorInput.value = toHex(parsed)
        textInput.value = raw || `rgba(${toRgbList(parsed)}, 0.25)`
      } else if (parsed) {
        const hex = toHex(parsed)
        colorInput.value = hex
        textInput.value = hex
      } else {
        textInput.value = raw
      }
    })
    updateExport()
  }

  const buildExportCss = () => {
    const lines = []
    const theme = root.getAttribute('data-bs-theme') || 'light'
    const palette = root.getAttribute('data-admin-palette') || 'default'
    lines.push(`/* Palette lab export — theme=${theme}, starting palette=${palette} */`)
    lines.push('[data-admin-palette="custom"] {')
    flatTokens.forEach(token => {
      const value = root.style.getPropertyValue(token.css).trim() || readComputed(token.css)
      if (!value) {
        return
      }
      lines.push(`  ${token.css}: ${value};`)
      if (token.rgb) {
        const rgb = root.style.getPropertyValue(token.rgb).trim() || readComputed(token.rgb)
        if (rgb) {
          lines.push(`  ${token.rgb}: ${rgb};`)
        }
      }
    })
    ;[
      'primary', 'secondary', 'success', 'danger', 'warning', 'info'
    ].forEach(name => {
      ;['text-emphasis', 'bg-subtle', 'border-subtle'].forEach(suffix => {
        const prop = `--bs-${name}-${suffix}`
        const inline = root.style.getPropertyValue(prop).trim()
        if (inline) {
          lines.push(`  ${prop}: ${inline};`)
        }
      })
      const on = root.style.getPropertyValue(`--admin-on-${name}`).trim()
      if (on) {
        lines.push(`  --admin-on-${name}: ${on};`)
      }
    })
    lines.push('}')
    return lines.join('\n')
  }

  const updateExport = () => {
    const out = document.querySelector('#palette-lab-export')
    if (out) {
      out.value = buildExportCss()
    }
  }

  const buildPickerUi = () => {
    const host = document.querySelector('#palette-lab-controls')
    if (!host) {
      return
    }

    TOKENS.forEach(group => {
      const heading = document.createElement('h3')
      heading.className = 'h6 text-body-secondary text-uppercase mt-3 mb-2'
      heading.textContent = group.group
      host.append(heading)

      group.items.forEach(token => {
        const row = document.createElement('div')
        row.className = 'palette-lab-row'

        const label = document.createElement('label')
        label.className = 'palette-lab-label'
        label.htmlFor = `lab-${token.key}`
        label.innerHTML = `<code>${token.css}</code>`

        const color = document.createElement('input')
        color.type = 'color'
        color.className = 'form-control form-control-color palette-lab-swatch'
        color.id = `lab-${token.key}`
        color.dataset.labColor = token.key
        color.title = token.css

        const text = document.createElement('input')
        text.type = 'text'
        text.className = 'form-control form-control-sm font-monospace'
        text.dataset.labText = token.key
        text.spellcheck = false
        text.autocomplete = 'off'
        text.ariaLabel = `${token.css} value`

        color.addEventListener('input', () => {
          setToken(token, color.value)
          if (token.key === 'primary') {
            syncInputsFromComputed()
          }
        })

        text.addEventListener('change', () => {
          setToken(token, text.value)
          if (token.key === 'primary') {
            syncInputsFromComputed()
          }
        })

        row.append(label, color, text)
        host.append(row)
      })
    })
  }

  const init = () => {
    buildPickerUi()
    syncInputsFromComputed()

    document.querySelector('#palette-lab-reset')?.addEventListener('click', () => {
      clearOverrides()
      syncInputsFromComputed()
    })

    document.querySelector('#palette-lab-copy')?.addEventListener('click', async () => {
      const css = buildExportCss()
      updateExport()
      try {
        await navigator.clipboard.writeText(css)
        const btn = document.querySelector('#palette-lab-copy')
        const prev = btn.textContent
        btn.textContent = 'Copied'
        setTimeout(() => {
          btn.textContent = prev
        }, 1500)
      } catch {
        document.querySelector('#palette-lab-export')?.select()
      }
    })

    deriveToggle()?.addEventListener('change', () => {
      const primary = flatTokens.find(t => t.key === 'primary')
      const text = document.querySelector('[data-lab-text="primary"]')
      if (primary && text?.value) {
        setToken(primary, text.value, { syncInputs: false })
      }
    })

    window.addEventListener('admin:palettechange', () => {
      clearOverrides()
      syncInputsFromComputed()
    })

    window.addEventListener('admin:themechange', () => {
      clearOverrides()
      syncInputsFromComputed()
    })
  }

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', init)
  } else {
    init()
  }
})()
