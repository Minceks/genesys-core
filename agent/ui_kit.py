"""Modern component kit installed into new projects, and the guidance that uses it."""

MODERN_DEPENDENCIES = {
    "@fontsource-variable/fraunces": "5.3.0",
    "@fontsource-variable/inter": "5.3.0",
    "@fontsource-variable/plus-jakarta-sans": "5.3.0",
    "@fontsource-variable/space-grotesk": "5.3.0",
    "class-variance-authority": "0.7.1",
    "clsx": "2.1.1",
    "date-fns": "4.4.0",
    "lucide-react": "1.65.0",
    "motion": "14.9.0",
    "radix-ui": "1.8.1",
    "react-router-dom": "7.18.5",
    "recharts": "3.10.1",
    "sonner": "2.0.8",
    "tailwind-merge": "3.7.0",
}
MODERN_DEV_DEPENDENCIES = {"@tailwindcss/vite": "4.3.3", "tailwindcss": "4.3.3"}

FOUNDATION_CSS = '''@import "tailwindcss";

/* Design tokens come from design-tokens.css. Utilities read them through this theme. */
@custom-variant dark (&:is(.dark *));

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--text);
  --color-surface: var(--surface);
  --color-card: var(--surface);
  --color-card-foreground: var(--text);
  --color-muted: color-mix(in oklab, var(--text) 6%, var(--surface));
  --color-muted-foreground: var(--muted);
  --color-primary: var(--accent);
  --color-primary-foreground: var(--accentText);
  --color-border: var(--border);
  --color-input: var(--border);
  --color-ring: var(--accent);
  --color-destructive: #dc2626;
  --font-sans: var(--font-body);
  --font-heading: var(--font-display);
  --radius-lg: var(--radius-control);
  --radius-xl: var(--radius-panel);
}

/* Unlayered rules would beat every utility, so project defaults stay in the base layer. */
@layer base {
  #root { width: 100%; min-height: 100dvh; min-width: 0; }
  img, video { height: auto; }
  img, video, canvas, svg { max-width: 100%; }
  input, select, textarea { max-width: 100%; }
  main, section, article, aside, form { min-width: 0; }
  p { overflow-wrap: anywhere; }
  button, a { touch-action: manipulation; }
  button:not(:disabled), [role="button"]:not(:disabled) { cursor: pointer; }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: .01ms !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
  }
}
'''

UI_KIT = {
    "src/lib/utils.js": '''import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs) {
  return twMerge(clsx(inputs))
}
''',
    "src/components/ui/button.jsx": '''import { cva } from 'class-variance-authority'
import { Slot } from 'radix-ui'
import { cn } from '../../lib/utils'

export const buttonVariants = cva(
  'inline-flex shrink-0 items-center justify-center gap-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground shadow-sm hover:brightness-110 active:brightness-95',
        secondary: 'bg-muted text-foreground hover:bg-border/70',
        outline: 'border border-border bg-surface text-foreground hover:bg-muted',
        ghost: 'text-foreground hover:bg-muted',
        destructive: 'bg-destructive text-white shadow-sm hover:brightness-110',
        link: 'text-primary underline-offset-4 hover:underline',
      },
      size: {
        default: 'min-h-11 px-4 py-2',
        sm: 'min-h-9 px-3 text-xs',
        lg: 'min-h-12 px-6 text-base',
        icon: 'size-11',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

export function Button({ className, variant, size, asChild = false, type, ...props }) {
  const Component = asChild ? Slot.Root : 'button'
  return <Component type={asChild ? type : type ?? 'button'} className={cn(buttonVariants({ variant, size }), className)} {...props} />
}
''',
    "src/components/ui/card.jsx": '''import { cn } from '../../lib/utils'

export function Card({ className, ...props }) {
  return <div className={cn('rounded-xl border border-border bg-card text-card-foreground shadow-sm', className)} {...props} />
}

export function CardHeader({ className, ...props }) {
  return <div className={cn('flex flex-col gap-1.5 p-6', className)} {...props} />
}

export function CardTitle({ className, ...props }) {
  return <h3 className={cn('font-heading text-lg leading-tight font-semibold tracking-tight', className)} {...props} />
}

export function CardDescription({ className, ...props }) {
  return <p className={cn('text-sm text-muted-foreground', className)} {...props} />
}

export function CardContent({ className, ...props }) {
  return <div className={cn('p-6 pt-0', className)} {...props} />
}

export function CardFooter({ className, ...props }) {
  return <div className={cn('flex items-center gap-3 p-6 pt-0', className)} {...props} />
}
''',
    "src/components/ui/input.jsx": '''import { cn } from '../../lib/utils'

export const fieldClasses = 'w-full rounded-lg border border-input bg-surface px-3 text-sm text-foreground shadow-xs transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-destructive/20'

export function Input({ className, type = 'text', ...props }) {
  return <input type={type} className={cn(fieldClasses, 'min-h-11 py-2', className)} {...props} />
}
''',
    "src/components/ui/textarea.jsx": '''import { cn } from '../../lib/utils'
import { fieldClasses } from './input'

export function Textarea({ className, ...props }) {
  return <textarea className={cn(fieldClasses, 'min-h-28 py-2.5 leading-relaxed', className)} {...props} />
}
''',
    "src/components/ui/select.jsx": '''import { ChevronDown } from 'lucide-react'
import { cn } from '../../lib/utils'
import { fieldClasses } from './input'

// A native select keeps phone pickers and automated browser checks reliable.
export function Select({ className, children, ...props }) {
  return (
    <div className="relative w-full">
      <select className={cn(fieldClasses, 'min-h-11 appearance-none py-2 pr-9', className)} {...props}>
        {children}
      </select>
      <ChevronDown aria-hidden="true" className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" />
    </div>
  )
}
''',
    "src/components/ui/label.jsx": '''import { cn } from '../../lib/utils'

export function Label({ className, ...props }) {
  return <label className={cn('text-sm leading-none font-medium text-foreground', className)} {...props} />
}
''',
    "src/components/ui/badge.jsx": '''import { cva } from 'class-variance-authority'
import { cn } from '../../lib/utils'

export const badgeVariants = cva('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium [&_svg]:size-3', {
  variants: {
    variant: {
      default: 'bg-primary text-primary-foreground',
      secondary: 'bg-muted text-foreground',
      outline: 'border border-border text-foreground',
      success: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300',
      warning: 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300',
      destructive: 'bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300',
    },
  },
  defaultVariants: { variant: 'default' },
})

export function Badge({ className, variant, ...props }) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
''',
    "src/components/ui/dialog.jsx": '''import { X } from 'lucide-react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import { cn } from '../../lib/utils'

export const Dialog = DialogPrimitive.Root
export const DialogTrigger = DialogPrimitive.Trigger
export const DialogClose = DialogPrimitive.Close

export function DialogContent({ className, children, ...props }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm" />
      <DialogPrimitive.Content
        className={cn('fixed top-1/2 left-1/2 z-50 grid max-h-[90dvh] w-[calc(100%-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 gap-4 overflow-y-auto rounded-xl border border-border bg-surface p-6 text-foreground shadow-xl', className)}
        {...props}
      >
        {children}
        <DialogPrimitive.Close aria-label="Close" className="absolute top-3 right-3 inline-flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-muted">
          <X className="size-4" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export function DialogHeader({ className, ...props }) {
  return <div className={cn('flex flex-col gap-1.5 pr-8', className)} {...props} />
}

export function DialogFooter({ className, ...props }) {
  return <div className={cn('flex flex-col-reverse gap-2 sm:flex-row sm:justify-end', className)} {...props} />
}

export function DialogTitle({ className, ...props }) {
  return <DialogPrimitive.Title className={cn('font-heading text-lg font-semibold tracking-tight', className)} {...props} />
}

export function DialogDescription({ className, ...props }) {
  return <DialogPrimitive.Description className={cn('text-sm text-muted-foreground', className)} {...props} />
}
''',
    "src/components/ui/tabs.jsx": '''import { Tabs as TabsPrimitive } from 'radix-ui'
import { cn } from '../../lib/utils'

export const Tabs = TabsPrimitive.Root

export function TabsList({ className, ...props }) {
  return <TabsPrimitive.List className={cn('inline-flex max-w-full gap-1 overflow-x-auto rounded-lg bg-muted p-1', className)} {...props} />
}

export function TabsTrigger({ className, ...props }) {
  return <TabsPrimitive.Trigger className={cn('min-h-9 rounded-md px-3 text-sm font-medium whitespace-nowrap text-muted-foreground transition-colors data-[state=active]:bg-surface data-[state=active]:text-foreground data-[state=active]:shadow-sm', className)} {...props} />
}

export function TabsContent({ className, ...props }) {
  return <TabsPrimitive.Content className={cn('mt-4 outline-none', className)} {...props} />
}
''',
    "src/components/ui/accordion.jsx": '''import { ChevronDown } from 'lucide-react'
import { Accordion as AccordionPrimitive } from 'radix-ui'
import { cn } from '../../lib/utils'

export const Accordion = AccordionPrimitive.Root

export function AccordionItem({ className, ...props }) {
  return <AccordionPrimitive.Item className={cn('border-b border-border', className)} {...props} />
}

export function AccordionTrigger({ className, children, ...props }) {
  return (
    <AccordionPrimitive.Header>
      <AccordionPrimitive.Trigger className={cn('group flex min-h-11 w-full items-center justify-between gap-4 py-4 text-left font-medium', className)} {...props}>
        {children}
        <ChevronDown aria-hidden="true" className="size-4 shrink-0 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
      </AccordionPrimitive.Trigger>
    </AccordionPrimitive.Header>
  )
}

export function AccordionContent({ className, ...props }) {
  return <AccordionPrimitive.Content className={cn('pb-4 text-sm leading-relaxed text-muted-foreground', className)} {...props} />
}
''',
    "src/components/ui/switch.jsx": '''import { Switch as SwitchPrimitive } from 'radix-ui'
import { cn } from '../../lib/utils'

export function Switch({ className, ...props }) {
  return (
    <SwitchPrimitive.Root className={cn('inline-flex h-6 w-11 shrink-0 items-center rounded-full bg-border p-0.5 transition-colors data-[state=checked]:bg-primary', className)} {...props}>
      <SwitchPrimitive.Thumb className="size-5 rounded-full bg-white shadow-sm transition-transform data-[state=checked]:translate-x-5" />
    </SwitchPrimitive.Root>
  )
}
''',
    "src/components/ui/table.jsx": '''import { cn } from '../../lib/utils'

export function Table({ className, ...props }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className={cn('w-full border-collapse text-sm', className)} {...props} />
    </div>
  )
}

export function TableHeader(props) {
  return <thead {...props} />
}

export function TableBody(props) {
  return <tbody {...props} />
}

export function TableRow({ className, ...props }) {
  return <tr className={cn('border-b border-border transition-colors hover:bg-muted/60', className)} {...props} />
}

export function TableHead({ className, ...props }) {
  return <th className={cn('px-3 py-2.5 text-left text-xs font-medium whitespace-nowrap text-muted-foreground', className)} {...props} />
}

export function TableCell({ className, ...props }) {
  return <td className={cn('px-3 py-3 align-middle', className)} {...props} />
}
''',
    "src/components/ui/skeleton.jsx": '''import { cn } from '../../lib/utils'

export function Skeleton({ className, ...props }) {
  return <div className={cn('animate-pulse rounded-lg bg-muted', className)} {...props} />
}
''',
    "src/components/ui/separator.jsx": '''import { cn } from '../../lib/utils'

export function Separator({ className, ...props }) {
  return <hr className={cn('border-0 border-t border-border', className)} {...props} />
}
''',
}

STACK_GUIDE = '''MODERN STACK: applies when package.json lists tailwindcss. Existing projects without it keep their own styling.
Installed and ready; use these rather than writing your own equivalents:
- Tailwind CSS 4 utilities are the default styling. Use semantic theme colors: bg-background, bg-surface, bg-card,
  bg-muted, bg-primary, text-foreground, text-muted-foreground, text-primary, text-primary-foreground, border-border.
  Use font-heading for display type. Do not hard-code hex colors, so the saved design system stays authoritative.
- Components, imported from "@/components/ui/<file>": button (Button, buttonVariants), card (Card, CardHeader, CardTitle,
  CardDescription, CardContent, CardFooter), input (Input), textarea (Textarea), select (Select: a styled native select,
  pass <option> children), label (Label), badge (Badge), dialog (Dialog, DialogTrigger, DialogContent, DialogHeader,
  DialogFooter, DialogTitle, DialogDescription, DialogClose), tabs (Tabs, TabsList, TabsTrigger, TabsContent),
  accordion (Accordion, AccordionItem, AccordionTrigger, AccordionContent), switch (Switch), table (Table, TableHeader,
  TableBody, TableRow, TableHead, TableCell), skeleton (Skeleton), separator (Separator). Use cn() from "@/lib/utils".
- lucide-react for every icon. Never use emoji or text symbols as interface icons.
- motion/react for restrained entrance and interaction motion; honor useReducedMotion.
- recharts for charts, react-router-dom (BrowserRouter) for multi-page products, date-fns for dates,
  and toast() from sonner for feedback. <Toaster /> is already mounted in src/main.jsx.
Do not add packages and do not write CSS files for what utilities can express.
Structure: App.jsx composes the app and routes; pages live in src/pages, sections and shared pieces in src/components,
state in src/projectLogic.js or src/hooks. One responsibility per file, normally under 200 lines.
Finish expected of current product work: a clear max-width container (max-w-6xl or max-w-7xl) with consistent gutters;
a sticky header using bg-background/80 and backdrop-blur; strong type contrast with tracking-tight headings and
text-balance; section spacing of py-16 to py-24 on public pages; rounded-xl surfaces with subtle borders and shadow-sm;
hover, focus and active feedback on everything interactive; skeletons or empty states rather than blank areas; and
intentional sm/md/lg responsive layouts. Show the actual product in the first screen, for example a realistic interface
preview built in JSX, instead of an abstract decoration. Prefer real hierarchy over identical card grids.'''

STACK_REVIEW = ('Apply MODERN STACK to the source: reject hard-coded hex colors in JSX, emoji used as icons, hand-rolled '
    'buttons, inputs or dialogs where the installed kit fits, imports of packages not in package.json, and single '
    'components that should be split. Do not change working behavior only to satisfy a style preference.')
