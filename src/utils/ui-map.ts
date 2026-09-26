// 1. ATOMIC UI (Shadcn Primitives)
// These are the small "bricks" like buttons and inputs.
export const CORE_UI = [
  "accordion", "alert", "badge", "button", "card", "checkbox", 
  "dialog", "input", "label", "popover", "select", "switch", "table"
] as const;

// 2. GENESYS MODULES (High-Level Sections)
// These are the "rooms" of your house.
export const GENESYS_COMPONENTS = [
  "navbar", "hero", "features", "how-it-works", "pricing", 
  "footer", "buy-credits", "referral", "showcase", "legal"
] as const;

export const UI_MAP = {
  core: CORE_UI,
  modules: GENESYS_COMPONENTS,
  basePath: "@/components/ui",
  modulePath: "@/components/genesys"
};