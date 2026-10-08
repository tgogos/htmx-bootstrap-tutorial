/*!
 * Color mode handling adapted from Bootstrap’s docs color-modes.js
 * https://getbootstrap.com/docs/5.3/customize/color-modes/
 * Copyright 2011-2025 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 *
 * Also persists an optional colour palette (data-admin-palette) and an
 * optional MIL-STD density profile (data-admin-profile) independently of
 * light / dark / auto.
 *
 * Also runs Bootstrap’s official client-side form validation snippet when
 * a form.needs-validation is present.
 */

(() => {
  'use strict'

  const getStoredTheme = () => localStorage.getItem('theme')
  const setStoredTheme = theme => localStorage.setItem('theme', theme)

  const getPreferredTheme = () => {
    const storedTheme = getStoredTheme()
    if (storedTheme) {
      return storedTheme
    }

    return 'auto'
  }

  const resolveTheme = theme => {
    if (theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }

    return theme
  }

  const setTheme = theme => {
    const resolved = resolveTheme(theme)
    const palette = document.documentElement.getAttribute('data-admin-palette')
    const effective = palette === 'night' ? 'dark' : resolved
    document.documentElement.setAttribute('data-bs-theme', effective)
    window.dispatchEvent(new CustomEvent('admin:themechange', {
      detail: { theme, resolved: effective }
    }))
  }

  setTheme(getPreferredTheme())

  const palettes = new Set(['default', 'teal', 'grey', 'mil-std', 'night'])

  const getStoredPalette = () => localStorage.getItem('admin-palette')
  const setStoredPalette = palette => localStorage.setItem('admin-palette', palette)

  const getPreferredPalette = () => {
    const storedPalette = getStoredPalette()
    return palettes.has(storedPalette) ? storedPalette : 'grey'
  }

  const setPalette = palette => {
    const next = palettes.has(palette) ? palette : 'grey'
    document.documentElement.setAttribute('data-admin-palette', next)
    // Night is dark-adaptation only; keep Bootstrap in dark mode while it is active.
    setTheme(getPreferredTheme())
    window.dispatchEvent(new CustomEvent('admin:palettechange', {
      detail: { palette: next }
    }))
  }

  setPalette(getPreferredPalette())

  const profiles = new Set(['off', 'mil-std'])

  const getStoredProfile = () => localStorage.getItem('admin-profile')
  const setStoredProfile = profile => localStorage.setItem('admin-profile', profile)

  const getPreferredProfile = () => {
    const stored = getStoredProfile()
    return profiles.has(stored) ? stored : 'off'
  }

  const setProfile = profile => {
    const next = profiles.has(profile) ? profile : 'off'
    if (next === 'off') {
      document.documentElement.removeAttribute('data-admin-profile')
    } else {
      document.documentElement.setAttribute('data-admin-profile', next)
    }
    window.dispatchEvent(new CustomEvent('admin:profilechange', {
      detail: { profile: next }
    }))
  }

  setProfile(getPreferredProfile())

  const showActiveTheme = (theme, focus = false) => {
    const themeSwitcher = document.querySelector('#bd-theme')

    if (!themeSwitcher) {
      return
    }

    const themeSwitcherText = document.querySelector('#bd-theme-text')
    const activeThemeIcon = themeSwitcher.querySelector('.theme-icon-active')
    const btnToActive = document.querySelector(`[data-bs-theme-value="${theme}"]`)

    if (!btnToActive) {
      return
    }

    document.querySelectorAll('[data-bs-theme-value]').forEach(element => {
      element.classList.remove('active')
      element.setAttribute('aria-pressed', 'false')
      const check = element.querySelector('[data-admin-theme-check]')
      if (check) {
        check.classList.add('d-none')
      }
    })

    btnToActive.classList.add('active')
    btnToActive.setAttribute('aria-pressed', 'true')
    const check = btnToActive.querySelector('[data-admin-theme-check]')
    if (check) {
      check.classList.remove('d-none')
    }

    const iconName = btnToActive.getAttribute('data-admin-theme-icon')
    if (activeThemeIcon && iconName) {
      activeThemeIcon.className = `bi ${iconName} theme-icon-active`
    }

    if (themeSwitcherText) {
      const themeSwitcherLabel = `${themeSwitcherText.textContent} (${btnToActive.dataset.bsThemeValue})`
      themeSwitcher.setAttribute('aria-label', themeSwitcherLabel)
    }

    if (focus) {
      themeSwitcher.focus()
    }
  }

  const showActivePalette = (palette, focus = false) => {
    const paletteSwitcher = document.querySelector('#admin-palette')

    if (!paletteSwitcher) {
      return
    }

    const btnToActive = document.querySelector(`[data-admin-palette-value="${palette}"]`)

    if (!btnToActive) {
      return
    }

    document.querySelectorAll('[data-admin-palette-value]').forEach(element => {
      element.classList.remove('active')
      element.setAttribute('aria-pressed', 'false')
      const check = element.querySelector('[data-admin-palette-check]')
      if (check) {
        check.classList.add('d-none')
      }
    })

    btnToActive.classList.add('active')
    btnToActive.setAttribute('aria-pressed', 'true')
    const check = btnToActive.querySelector('[data-admin-palette-check]')
    if (check) {
      check.classList.remove('d-none')
    }

    const paletteName = btnToActive.textContent.replace(/\s+/g, ' ').trim()
    paletteSwitcher.setAttribute('aria-label', `Palette (${paletteName})`)

    if (focus) {
      paletteSwitcher.focus()
    }
  }

  const showActiveProfile = (profile, focus = false) => {
    const profileSwitcher = document.querySelector('#admin-profile')

    if (!profileSwitcher) {
      return
    }

    const profileSwitch = document.querySelector('[data-admin-profile-switch]')
    if (profileSwitch) {
      profileSwitch.checked = profile === 'mil-std'
    }

    const label = profile === 'mil-std' ? 'On' : 'Off'
    profileSwitcher.setAttribute('aria-label', `Profile (${label})`)

    if (focus) {
      profileSwitcher.focus()
    }
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const storedTheme = getStoredTheme()
    if (storedTheme !== 'light' && storedTheme !== 'dark') {
      setTheme(getPreferredTheme())
    }
  })

  window.addEventListener('DOMContentLoaded', () => {
    const themeForUi = () =>
      getPreferredPalette() === 'night' ? 'dark' : getPreferredTheme()

    showActiveTheme(themeForUi())
    showActivePalette(getPreferredPalette())
    showActiveProfile(getPreferredProfile())

    document.querySelectorAll('[data-bs-theme-value]').forEach(toggle => {
      toggle.addEventListener('click', () => {
        const theme = toggle.getAttribute('data-bs-theme-value')
        setStoredTheme(theme)
        setTheme(theme)
        showActiveTheme(themeForUi(), true)
      })
    })

    document.querySelectorAll('[data-admin-palette-value]').forEach(toggle => {
      toggle.addEventListener('click', () => {
        const palette = toggle.getAttribute('data-admin-palette-value')
        setStoredPalette(palette)
        setPalette(palette)
        showActivePalette(palette, true)
        showActiveTheme(themeForUi())
      })
    })

    const profileSwitch = document.querySelector('[data-admin-profile-switch]')
    if (profileSwitch) {
      profileSwitch.addEventListener('change', () => {
        const profile = profileSwitch.checked ? 'mil-std' : 'off'
        setStoredProfile(profile)
        setProfile(profile)
        showActiveProfile(profile)
      })

      // Keep the menu open while flipping the switch so the density change is visible.
      document.querySelectorAll('[data-admin-profile-row]').forEach(row => {
        row.addEventListener('click', event => {
          event.stopPropagation()
        })
      })
    }

    document.querySelectorAll('.needs-validation').forEach(form => {
      form.addEventListener('submit', event => {
        if (!form.checkValidity()) {
          event.preventDefault()
          event.stopPropagation()
        }

        form.classList.add('was-validated')
      })
    })

    const linkUrl = href => {
      try {
        return new URL(href, window.location.origin)
      } catch (error) {
        return null
      }
    }

    const setHashNavActive = () => {
      const current = window.location.pathname.replace(/\/$/, '') || '/'
      const { hash } = window.location
      const links = Array.from(document.querySelectorAll('.admin-sidebar a.nav-link[href]'))
        .filter(link => {
          const url = linkUrl(link.getAttribute('href'))
          if (!url) {
            return false
          }
          const target = url.pathname.replace(/\/$/, '') || '/'
          return target === current
        })
      const sectionLinks = links.filter(link => (link.getAttribute('href') || '').includes('#'))

      if (!sectionLinks.length) {
        return
      }

      const pageLink = links.find(link => !(link.getAttribute('href') || '').includes('#'))
      let match = hash
        ? links.find(link => {
          const url = linkUrl(link.getAttribute('href'))
          return url && url.hash === hash
        })
        : pageLink

      if (!match) {
        match = pageLink || sectionLinks[0]
      }

      links.forEach(link => {
        link.classList.remove('active')
        link.removeAttribute('aria-current')
      })

      match.classList.add('active')
      match.setAttribute('aria-current', 'page')
    }

    setHashNavActive()
    window.addEventListener('hashchange', setHashNavActive)
  })
})()
