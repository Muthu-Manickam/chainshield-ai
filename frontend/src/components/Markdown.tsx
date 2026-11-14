// Tiny renderer for report and chat text: # / ## headings, "- " bullets, **bold**, paragraphs.
const bold = (text: string) => text.split(/\*\*(.+?)\*\*/).map((part, i) => (i % 2 ? <strong key={i}>{part}</strong> : part))

export default function Markdown({ text }: { text: string }) {
  return (
    <div className="flex flex-col gap-1.5 text-sm">
      {text.split("\n").filter((line) => line.trim()).map((line, i) => {
        if (line.startsWith("## ")) return <h4 key={i} className="mt-2 font-semibold">{bold(line.slice(3))}</h4>
        if (line.startsWith("# ")) return <h3 key={i} className="mt-2 text-base font-semibold">{bold(line.slice(2))}</h3>
        if (line.startsWith("- ")) return <li key={i} className="ml-5 list-disc">{bold(line.slice(2))}</li>
        return <p key={i}>{bold(line)}</p>
      })}
    </div>
  )
}
