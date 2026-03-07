"use client"

import { cva } from 'class-variance-authority'
import {
  FieldError as AriaFieldError,
  Group as AriaGroup,
  Label as AriaLabel,
  Text as AriaText,
  composeRenderProps,
} from 'react-aria-components'

import { cn } from '@/lib/utils'

const labelVariants = cva([
  'text-sm font-medium leading-none',
  'data-[disabled]:cursor-not-allowed data-[disabled]:opacity-70',
  'group-data-[invalid]:text-destructive',
])

const Label = ({ className, ...props }) => (
  <AriaLabel className={cn(labelVariants(), className)} {...props} />
)

function FormDescription({ className, ...props }) {
  return (
    <AriaText
      className={cn('text-sm text-muted-foreground', className)}
      {...props}
      slot="description"
    />
  )
}

function FieldError({ className, ...props }) {
  return (
    <AriaFieldError
      className={cn('text-sm font-medium text-destructive', className)}
      {...props}
    />
  )
}

const fieldGroupVariants = cva('', {
  variants: {
    variant: {
      default: [
        'relative flex h-10 w-full items-center overflow-hidden rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background',
        'data-[focus-within]:outline-none data-[focus-within]:ring-2 data-[focus-within]:ring-ring data-[focus-within]:ring-offset-2',
        'data-[disabled]:opacity-50',
      ],
      ghost: '',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
})

function FieldGroup({ className, variant, ...props }) {
  return (
    <AriaGroup
      className={composeRenderProps(className, (nextClassName) =>
        cn(fieldGroupVariants({ variant }), nextClassName)
      )}
      {...props}
    />
  )
}

export {
  Label,
  FieldGroup,
  FieldError,
  FormDescription,
}
