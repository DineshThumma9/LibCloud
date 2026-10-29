import { useEffect, useMemo, useRef, useState } from 'react'
import type { CSSProperties } from 'react'
import { Toaster } from 'sonner'
import { CloudCanvas } from './components/CloudCanvas'
import { Toolbar } from './components/Toolbar'
import { useCloudStream } from './hooks/useCloudStream'
import { useShare } from './hooks/useShare'
import { getChipFill, normalizeIcon } from './lib/color'
import { measureIconAppearance, setsEqual } from './lib/icon'
import { PRESETS, SIZES, presetCssVars, type PresetId, type SizeId, type SortId } from './lib/presets'
import { useCloudStore } from './state'

function App() {
  const [maxCount, setMaxCount] = useState<string>('100')
  const [username, setUsername] = useState<string>('')
  const [sort, setSort] = useState<SortId>('most-used')
  const [presetId, setPresetId] = useState<PresetId>('ink')
  const [sizeId, setSizeId] = useState<SizeId>('web')
  const [showMissingLogos, setShowMissingLogos] = useState<boolean>(false)
  const [transparentChips, setTransparentChips] = useState<boolean>(false)
  const [token, setToken] = useState<string>('')

  const logosMap = useCloudStore((s) => s.logos)
  const logos = useMemo(() => Array.from(logosMap.values()), [logosMap])
  const graphRef = useRef<SVGSVGElement | null>(null)

  const preset = PRESETS[presetId]
  const size = SIZES[sizeId]

  const maxLogos = useMemo(() => {
    const parsed = Number.parseInt(maxCount, 10)
    return Number.isFinite(parsed) ? Math.min(500, Math.max(1, parsed)) : 100
  }, [maxCount])

  const visibleLogos = useMemo(() => {
    const filtered = showMissingLogos ? logos : logos.filter((l) => Boolean(l.icon))
    const sorted = [...filtered].sort((a, b) => {
      const diff = sort === 'least-used' ? a.count - b.count : b.count - a.count
      return diff !== 0 ? diff : a.name.localeCompare(b.name)
    })
    return sorted.slice(0, maxLogos)
  }, [logos, maxLogos, showMissingLogos, sort])

  const renderedIcons = useMemo(() => {
    const icons = new Map<string, string>()
    for (const logo of visibleLogos) {
      if (logo.icon) icons.set(logo.id, normalizeIcon(logo.icon) ?? logo.icon)
    }
    return icons
  }, [visibleLogos])

  const [measuredLightIds, setMeasuredLightIds] = useState<Set<string>>(
    () => new Set()
  )
  const [blankIconIds, setBlankIconIds] = useState<Set<string>>(
    () => new Set()
  )

  useEffect(() => {
    let cancelled = false
    const entries: { id: string; icon: string }[] = []
    for (const logo of visibleLogos) {
      const icon = renderedIcons.get(logo.id) ?? logo.icon
      if (icon) entries.push({ id: logo.id, icon })
    }
    if (entries.length === 0) return

    void (async () => {
      const lightIds = new Set<string>()
      const blankIds = new Set<string>()
      await Promise.all(
        entries.map(async ({ id, icon }) => {
          const appearance = await measureIconAppearance(icon)
          if (appearance.isLight) lightIds.add(id)
          if (appearance.isBlank) blankIds.add(id)
        })
      )
      if (!cancelled) {
        setMeasuredLightIds((previous) =>
          setsEqual(previous, lightIds) ? previous : lightIds
        )
        setBlankIconIds((previous) =>
          setsEqual(previous, blankIds) ? previous : blankIds
        )
      }
    })()

    return () => {
      cancelled = true
    }
  }, [visibleLogos, renderedIcons])

  const chipFills = useMemo(() => {
    const fills = new Map<string, string>()
    for (const logo of visibleLogos) {
      fills.set(
        logo.id,
        getChipFill(
          renderedIcons.get(logo.id),
          preset.dark,
          measuredLightIds.has(logo.id)
        )
      )
    }
    return fills
  }, [visibleLogos, renderedIcons, preset.dark, measuredLightIds])

  const { isLoading, statusText, handleGenerate, abortStream } = useCloudStream({
    username,
    token,
  })

  const { share } = useShare({
    graphRef,
    username,
    preset,
    size,
    hasLogos: visibleLogos.length > 0,
  })

  useEffect(() => {
    const root = document.documentElement
    for (const [name, value] of Object.entries(presetCssVars(preset))) {
      root.style.setProperty(name, value)
    }
    document
      .querySelector('meta[name="theme-color"]')
      ?.setAttribute('content', preset.tokens.canvas)
  }, [preset])

  return (
    <div
      data-theme={preset.id}
      style={presetCssVars(preset) as CSSProperties}
      className="flex min-h-screen flex-col bg-canvas text-ink transition-colors duration-200"
    >
      <Toaster richColors position="top-right" theme={preset.dark ? 'dark' : 'light'} />

      <Toolbar
        username={username}
        token={token}
        maxCount={maxCount}
        presetId={presetId}
        sizeId={sizeId}
        sort={sort}
        isLoading={isLoading}
        showMissingLogos={showMissingLogos}
        transparentChips={transparentChips}
        onUsernameChange={setUsername}
        onTokenChange={setToken}
        onMaxCountChange={setMaxCount}
        onPresetChange={setPresetId}
        onSizeChange={setSizeId}
        onSortChange={setSort}
        onShare={share}
        onToggleMissingLogos={() => setShowMissingLogos(!showMissingLogos)}
        onToggleTransparentChips={() => setTransparentChips(!transparentChips)}
        onGenerate={handleGenerate}
        onAbort={abortStream}
      />

      <CloudCanvas
        logos={visibleLogos}
        renderedIcons={renderedIcons}
        blankIconIds={blankIconIds}
        chipFills={chipFills}
        preset={preset}
        size={size}
        sort={sort}
        transparentChips={transparentChips}
        isLoading={isLoading}
        statusText={statusText}
        seed={username || 'libcloud'}
        graphRef={graphRef}
      />

      <section id="spacer" className="border-t border-line"></section>
    </div>
  )
}

export default App
