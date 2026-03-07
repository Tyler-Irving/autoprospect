"use client"

import { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react'

import { cn } from '@/lib/utils'
const SelectCtx = createContext(null)

function collectOptions(node, out = []) {
  if (!node) return out
  const list = Array.isArray(node) ? node : [node]
  list.forEach((child) => {
    if (!child || typeof child !== 'object') return
    if (child.type?.displayName === 'SelectItem') {
      out.push({ id: String(child.props.id), label: child.props.children })
    }
    if (child.props?.children) collectOptions(child.props.children, out)
  })
  return out
}

const Select = ({ className, children, selectedKey, onSelectionChange, placeholder }) => {
  const [open, setOpen] = useState(false)
  const rootRef = useRef(null)
  const options = useMemo(() => collectOptions(children, []), [children])

  useEffect(() => {
    const onDown = (e) => {
      if (!rootRef.current?.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    return () => document.removeEventListener('mousedown', onDown)
  }, [])

  const value = {
    open,
    setOpen,
    options,
    selectedKey: selectedKey == null ? null : String(selectedKey),
    onSelectionChange,
    placeholder,
  }

  return (
    <SelectCtx.Provider value={value}>
      <div ref={rootRef} className={cn('group relative flex flex-col gap-2', className)}>
        {children}
      </div>
    </SelectCtx.Provider>
  )
}

const Label = ({ className, ...props }) => (
  <label className={cn('text-sm font-medium leading-none', className)} {...props} />
)

const SelectValue = ({ className }) => {
  const ctx = useContext(SelectCtx)
  if (!ctx) return null
  const selected = ctx.options.find((opt) => opt.id === ctx.selectedKey)
  return (
    <span
      className={cn(
        'line-clamp-1',
        !selected && 'text-muted-foreground',
        className
      )}
    >
      {selected?.label || ctx.placeholder || 'Select an option'}
    </span>
  )
}

const SelectTrigger = ({ className, children, ...props }) => {
  const ctx = useContext(SelectCtx)
  if (!ctx) return null
  return (
    <button
      type="button"
      onClick={() => ctx.setOpen((v) => !v)}
      className={cn(
        'flex h-10 w-full items-center justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
        className
      )}
      {...props}
    >
      {children}
      <svg
        aria-hidden="true"
        className="size-4 opacity-50"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m6 9 6 6 6-6" />
      </svg>
    </button>
  )
}

const SelectPopover = ({ className, children }) => {
  const ctx = useContext(SelectCtx)
  if (!ctx?.open) return null
  return (
    <div
      className={cn(
        'absolute z-50 mt-1 w-full rounded-md border bg-popover text-popover-foreground shadow-md outline-none',
        className
      )}
    >
      {children}
    </div>
  )
}

const SelectListBox = ({ className, children }) => (
  <div
    className={cn(
      'max-h-[280px] overflow-auto p-1 outline-none [clip-path:inset(0_0_0_0_round_calc(var(--radius)-2px))]',
      className
    )}
  >
    {children}
  </div>
)

const SelectItem = ({ id, children, className }) => {
  const ctx = useContext(SelectCtx)
  if (!ctx) return null
  const key = String(id)
  const selected = ctx.selectedKey === key
  return (
    <button
      type="button"
      onClick={() => {
        ctx.onSelectionChange?.(key)
        ctx.setOpen(false)
      }}
      className={cn(
        'relative flex w-full select-none items-center rounded-sm px-2 py-1.5 text-sm text-left outline-none',
        'hover:bg-accent hover:text-accent-foreground',
        selected && 'bg-accent text-accent-foreground pl-8',
        className
      )}
    >
      {selected && (
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
      {children}
    </button>
  )
}
SelectItem.displayName = 'SelectItem'

const SelectHeader = ({ className, ...props }) => (
  <div className={cn('py-1.5 pl-8 pr-2 text-sm font-semibold', className)} {...props} />
)

const SelectSection = ({ children }) => <div>{children}</div>
const SelectCollection = ({ children }) => <>{children}</>

const FieldError = ({ className, ...props }) => (
  <p className={cn('text-sm font-medium text-destructive', className)} {...props} />
)

function JollySelect({ label, description, errorMessage, children, className, ...props }) {
  return (
    <Select className={cn('group flex flex-col gap-2', className)} {...props}>
      <Label>{label}</Label>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      {description && <p className="text-sm text-muted-foreground">{description}</p>}
      <FieldError>{errorMessage}</FieldError>
      <SelectPopover>
        <SelectListBox>{children}</SelectListBox>
      </SelectPopover>
    </Select>
  )
}

export {
  Select,
  Label,
  SelectValue,
  SelectTrigger,
  SelectItem,
  SelectPopover,
  SelectHeader,
  SelectListBox,
  SelectSection,
  SelectCollection,
  JollySelect,
}
