"use client"

import {
  Collection as AriaCollection,
  Header as AriaHeader,
  ListBox as AriaListBox,
  ListBoxItem as AriaListBoxItem,
  composeRenderProps,
  Section as AriaSection,
} from 'react-aria-components'

import { cn } from '@/lib/utils'

const ListBoxSection = AriaSection

const ListBoxCollection = AriaCollection

function ListBox({ className, ...props }) {
  return (
    <AriaListBox
      className={composeRenderProps(className, (nextClassName) =>
        cn(
          nextClassName,
          'group overflow-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md outline-none',
          'data-[empty]:p-6 data-[empty]:text-center data-[empty]:text-sm'
        )
      )}
      {...props}
    />
  )
}

const ListBoxItem = ({ className, children, ...props }) => {
  return (
    <AriaListBoxItem
      textValue={
        props.textValue || (typeof children === 'string' ? children : undefined)
      }
      className={composeRenderProps(className, (nextClassName) =>
        cn(
          'relative flex w-full cursor-default select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none',
          'data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
          'data-[focused]:bg-accent data-[focused]:text-accent-foreground',
          'data-[hovered]:bg-accent data-[hovered]:text-accent-foreground',
          'data-[selection-mode]:pl-8',
          nextClassName
        )
      )}
      {...props}
    >
      {composeRenderProps(children, (nextChildren, renderProps) => (
        <>
          {renderProps.isSelected && (
            <span className="absolute left-2 flex size-4 items-center justify-center">
              <svg
                className="size-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M20 6 9 17l-5-5" />
              </svg>
            </span>
          )}
          {nextChildren}
        </>
      ))}
    </AriaListBoxItem>
  )
}

function ListBoxHeader({ className, ...props }) {
  return (
    <AriaHeader
      className={cn('py-1.5 pl-8 pr-2 text-sm font-semibold', className)}
      {...props}
    />
  )
}

export {
  ListBox,
  ListBoxItem,
  ListBoxHeader,
  ListBoxSection,
  ListBoxCollection,
}
