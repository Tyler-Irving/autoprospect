import {
  Label,
  Select,
  SelectItem,
  SelectListBox,
  SelectPopover,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export function SelectDemo() {
  return (
    <Select className="w-[200px]" placeholder="Select an animal">
      <Label>Favorite Animal</Label>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectPopover>
        <SelectListBox>
          <SelectItem>Aardvark</SelectItem>
          <SelectItem>Cat</SelectItem>
          <SelectItem>Dog</SelectItem>
          <SelectItem>Kangaroo</SelectItem>
          <SelectItem>Panda</SelectItem>
          <SelectItem>Snake</SelectItem>
        </SelectListBox>
      </SelectPopover>
    </Select>
  )
}
