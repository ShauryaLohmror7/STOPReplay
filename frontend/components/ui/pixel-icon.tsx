import type { SVGProps } from 'react'

// One 16 × 16 grid across the interface. Integer-edged, filled geometry stays
// crisp at small sizes; decorative icons inherit the accessible control label.
const paths = {
  flag: 'M2 1h2v1h10v6H4v7H2Zm2 3v2h8V4Z',
  plus: 'M7 2h2v5h5v2H9v5H7V9H2V7h5Z',
  close: 'M2 2h2v2h2v2h4V4h2V2h2v2h-2v2h-2v4h2v2h2v2h-2v-2h-2v-2H6v2H4v2H2v-2h2v-2h2V6H4V4H2Z',
  arrowRight: 'M2 7h8V5H8V3h2v2h2v2h2v2h-2v2h-2v2H8v-2h2V9H2Z',
  arrowUpRight: 'M5 2h9v9h-2V6h-2v2H8v2H6v2H4v2H2v-2h2v-2h2V8h2V6h2V4H5Z',
  arrowDownRight: 'M2 2h2v2h2v2h2v2h2v2h2V5h2v9H5v-2h5v-2H8V8H6V6H4V4H2Z',
  chevronLeft: 'M9 2h2v2H9v2H7v4h2v2h2v2H9v-2H7v-2H5V6h2V4h2Z',
  chevronRight: 'M5 2h2v2h2v2h2v4H9v2H7v2H5v-2h2v-2h2V6H7V4H5Z',
  check: 'M1 7h2v2h2v2h2V9h2V7h2V5h2V3h2v4h-2v2h-2v2H9v2H7v2H5v-2H3v-2H1Z',
  mail: 'M1 3h14v10H1Zm2 2v1h2v2h2v2h2V8h2V6h2V5Zm0 4v2h2V9Zm8 0v2h2V9Z',
  message: 'M1 2h14v10H7v2H5v1H3v-3H1Zm2 2v6h2v2h2v-2h6V4Zm2 2h6v2H5Z',
  file: 'M3 1h7v2h2v2h2v10H3Zm2 2v10h7V7H8V3Zm5 2v1h1V5ZM6 9h4v1H6Zm0 2h4v1H6Z',
  lock: 'M5 1h6v2h2v4h2v8H1V7h2V3h2Zm0 2v4h6V3Zm2 6v3h2V9Z',
  history: 'M5 1h7v2h2v2h2v7h-2v2h-2v2H5v-2H3v-2h2v2h7v-2h2V5h-2V3H5v2H3v2h3v2H0V3h2v2h1V3h2Zm2 4h2v4h3v2H7Z',
  terminal: 'M1 2h14v12H1Zm2 2v8h10V4Zm1 1h2v2h2v2H6v2H4V9h2V7H4Zm5 4h3v2H9Z',
  layers: 'M3 1h10v2H3ZM1 4h14v3H1Zm2 4h10v3H3Zm2 4h6v3H5Z',
  search: 'M3 1h6v2h2v6H9v2h2v2h2v2h-2v-2H9v-2H3V9H1V3h2Zm0 2v6h6V3Z',
  storage: 'M2 1h12v4H2Zm2 1v2h2V2ZM2 6h12v4H2Zm2 1v2h2V7ZM2 11h12v4H2Zm2 1v2h2v-2Z',
  analysis: 'M6 1h4v2H6ZM3 3h3v2H3Zm7 0h3v2h-3ZM1 5h2v6H1Zm12 0h2v6h-2ZM5 5h6v2H5Zm0 2h2v6H5Zm4 2h2v6H9ZM3 11h2v4H3Zm8 0h2v2h-2ZM7 13h2v2H7Z',
  network: 'M6 1h4v4H6ZM7 5h2v2h5v4h1v4h-4v-4h1V9H9v2h1v4H6v-4h1V9H4v2h1v4H1v-4h1V7h5Z',
  signal: 'M0 2h2v2H0Zm2 2h2v8H2Zm-2 8h2v2H0ZM14 2h2v2h-2Zm-2 2h2v8h-2Zm2 8h2v2h-2ZM6 5h4v4H6Zm1 4h2v6H7Z',
  return: 'M5 1h2v2H5v2H3v2h2v2h2v2H5V9H3V7H1V5h2V3h2Zm0 4h10v10H8v-2h5V7H5Z',
  play: 'M4 2h2v2h3v2h3v2h2v1h-2v2H9v2H6v2H4Z',
  pause: 'M3 2h3v12H3Zm7 0h3v12h-3Z',
} as const

export type PixelIconName = keyof typeof paths
export function PixelIcon({ name, size = 16, ...props }: Omit<SVGProps<SVGSVGElement>, 'name'> & { name: PixelIconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" shapeRendering="crispEdges" aria-hidden="true" focusable="false" {...props}><path d={paths[name]} fillRule="evenodd"/></svg>
}
