import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

// A shadcn Select over plain string options; `all` adds a first item (value "all") with that label.
export default function OptionSelect({ value, onChange, options, all, className = "w-44", size }: {
  value: string
  onChange: (value: string) => void
  options: readonly string[]
  all?: string
  className?: string
  size?: "sm" | "default"
}) {
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger size={size} className={`bg-background ${className}`}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {all && <SelectItem value="all">{all}</SelectItem>}
        {options.map((option) => (
          <SelectItem key={option} value={option} className="capitalize">
            {option.replaceAll("_", " ")}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
