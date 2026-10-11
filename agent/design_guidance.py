"""Project-specific visual guidance for generated applications."""

import hashlib

DESIGN_DIRECTIONS = (
    "Warm editorial: ivory surfaces, ink text, terracotta accents, expressive headings and generous whitespace.",
    "Botanical modern: pale sage surfaces, deep forest text, restrained emerald accents and soft geometry.",
    "Quiet luxury: warm stone surfaces, charcoal text, muted plum accents and precise typography.",
    "Crisp product: cool gray surfaces, graphite text, vivid indigo accents and compact, clear data layouts.",
    "Creative studio: cream surfaces, near-black text, coral accents and confident asymmetric composition.",
    "Contemporary dark: deep charcoal surfaces, soft white text, mint accents and carefully layered panels.",
)


def project_design_guidance(project_id: str) -> str:
    index = int.from_bytes(hashlib.sha256(project_id.encode()).digest()[:4], "big")
    direction = DESIGN_DIRECTIONS[index % len(DESIGN_DIRECTIONS)]
    return f"""
VISUAL DESIGN FOR THIS USER APPLICATION
Treat visual design as part of completing the requested application.
User-specified brand, colors, reference style and light/dark preferences take priority.
For a new app without a requested style, consider this project-specific starting direction:
{direction}
Adapt the direction to the app's purpose and audience; do not force it onto an established design.
The GeneSys builder's white-and-blue brand is not a default theme for generated apps.
Before editing, choose a coherent palette, typography, spacing, layout and shape language.
Implement them in the project's stylesheet using shared CSS variables for surfaces, text,
accents, borders, spacing and corners. Record the chosen direction in a CSS comment in that
same stylesheet edit, so subsequent requests can retain the design without an extra setup step.
On an existing app, inspect and reuse its visual tokens; change its theme only when requested.
Create a composed page with a clear focal point, useful information hierarchy, balanced density,
purposeful whitespace, polished typography and details appropriate to the requested product.
For photographers' portfolios and other image-led sites, include actual photographic images
in the hero and gallery, not blank cards, gradients or icon substitutes. Use the user's provided
photos first. Without uploaded photos, use representative stock sample images, label the collection
as sample photography, and never claim these are the user's own photographs. For sample sources use
https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1200&q=80
https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80
https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80
Use descriptive alt text, responsive widths, aspect ratios, object-fit, and lazy loading below the fold.
Make image collections easy to replace with the user's real photos. Images must load in verification.
Avoid applying the same card grid, gradients, blue accents or generic hero to every request.
Keep text legible: aim for WCAG AA contrast, visible keyboard focus, descriptive labels,
usable touch targets and responsive layouts without horizontal overflow.
Use hover/active states and restrained transitions; respect prefers-reduced-motion.
Use semantic HTML and actual installed styling tools. The clean starter has plain CSS;
Tailwind class names do not work unless Tailwind has actually been configured.
Keep each implementation tool call small and complete. Use focused patches for existing files;
split large new applications into components instead of emitting the entire project in one response.
Never leave placeholder code to fit a response budget.
Build the requested interactions with meaningful loading, empty, error and success states.
Do not use dead buttons, unrelated platform navigation or fake completed integrations.
For ordinary user-created app data, persist changes across reloads. Import the provided
usePersistentState hook from src/usePersistentState.js when present, use a stable descriptive
storage key, validate loaded data shape when needed and show storageError to the user.
Do not store secrets or passwords in browser storage. Browser storage is local to this
device; for shared multi-user data, require a real backend and database instead of claiming sync.
For an existing application, preserve its data keys and schema; do not discard saved data.
When browser verification is available, inspect the actual rendered application for layout,
readable content, clipping and the requested UI. A clean console alone is not visual proof.
"""
