"use client"

import {
  Dialog as AriaDialog,
  DialogTrigger as AriaDialogTrigger,
  Popover as AriaPopover,
  composeRenderProps,
} from 'react-aria-components'

import { cn } from '@/lib/utils'

const PopoverTrigger = AriaDialogTrigger

const Popover = ({ className, offset = 4, ...props }) => (
  <AriaPopover
    offset={offset}
    className={composeRenderProps(className, (nextClassName) =>
      cn(
        'z-50 rounded-md border bg-popover text-popover-foreground shadow-md outline-none',
        'data-[entering]:animate-in data-[entering]:fade-in-0 data-[entering]:zoom-in-95',
        'data-[exiting]:animate-out data-[exiting]:fade-out-0 data-[exiting]:zoom-out-95',
        'data-[placement=bottom]:slide-in-from-top-2 data-[placement=left]:slide-in-from-right-2 data-[placement=right]:slide-in-from-left-2 data-[placement=top]:slide-in-from-bottom-2',
        nextClassName
      )
    )}
    {...props}
  />
)

function PopoverDialog({ className, ...props }) {
  return (
    <AriaDialog className={cn('p-4 outline outline-0', className)} {...props} />
  )
}

export { Popover, PopoverTrigger, PopoverDialog }

