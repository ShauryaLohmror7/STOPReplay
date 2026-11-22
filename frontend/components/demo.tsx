import { AsciiArt } from "@/components/ui/electric-gaze"

// Reference demo only; it is deliberately not mounted in the portrait intro.
export default function AsciiArtDemo() {
  return (
    <div className="relative h-screen w-full overflow-hidden">
      <AsciiArt className="h-full w-full" />
    </div>
  )
}
