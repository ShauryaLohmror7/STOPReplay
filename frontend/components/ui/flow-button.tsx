"use client"

import type { ComponentPropsWithoutRef } from 'react'
import { PixelIcon } from '@/components/ui/pixel-icon'
import { cn } from '@/lib/utils'

// User-supplied FlowButton choreography, adapted to the signature blue/black palette.
type FlowButtonProps = ComponentPropsWithoutRef<'button'> & { text?: string }

export function FlowButton({ text = 'Try it for yourself', className, type = 'button', ...props }: FlowButtonProps) {
  return (
    <button
      {...props}
      type={type}
      className={cn('flow-button group relative isolate flex items-center gap-1 overflow-hidden rounded-[100px] border-[1.5px] border-[#6bbed2] bg-[#6bbed2] px-8 py-3 text-sm font-normal text-black cursor-pointer transition-all duration-[600ms] ease-[cubic-bezier(0.23,1,0.32,1)] hover:border-[#9cddeb] hover:rounded-[12px] focus-visible:rounded-[12px] active:scale-[0.95] motion-reduce:transition-none', className)}
    >
      <PixelIcon name="arrowRight" aria-hidden="true" className="absolute z-[2] left-[-25%] h-4 w-4 fill-current text-black transition-all duration-[800ms] ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:left-4 group-focus-visible:left-4 motion-reduce:transition-none" />
      <span className="relative z-[1] -translate-x-3 transition-transform duration-[800ms] ease-out group-hover:translate-x-3 group-focus-visible:translate-x-3 motion-reduce:transition-none">{text}</span>
      <span aria-hidden="true" className="flow-button-fill absolute top-1/2 left-1/2 h-4 w-4 -translate-x-1/2 -translate-y-1/2 rounded-[50%] bg-[#9cddeb] opacity-0 transition-all duration-[800ms] ease-[cubic-bezier(0.19,1,0.22,1)] group-hover:h-[320px] group-hover:w-[320px] group-hover:opacity-100 group-focus-visible:h-[320px] group-focus-visible:w-[320px] group-focus-visible:opacity-100 motion-reduce:transition-none" />
      <PixelIcon name="arrowRight" aria-hidden="true" className="absolute z-[2] right-4 h-4 w-4 fill-current text-black transition-all duration-[800ms] ease-[cubic-bezier(0.34,1.56,0.64,1)] group-hover:right-[-25%] group-focus-visible:right-[-25%] motion-reduce:transition-none" />
    </button>
  )
}
