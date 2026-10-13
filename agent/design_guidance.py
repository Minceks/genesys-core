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


PURPOSE_DIRECTIONS = {
    'website': 'Public-facing website: expressive editorial hierarchy, a strong visual hero, meaningful navigation, varied content sections and a useful footer. Compose for visitors; avoid an admin dashboard or spreadsheet as the main experience.',
    'portfolio': 'Art direction first: an oversized photographic hero, restrained editorial type, warm neutral canvas and carefully cropped image sequences. Let the work carry the visual identity.',
    'store': 'Modern commerce: generous product imagery, clear prices and readable categories, with a restrained purchase accent and a coherent browsing rhythm.',
    'dashboard': 'Modern workspace: neutral surfaces, precise alignment, strong metric typography, useful data density and one purposeful action accent.',
    'app': 'Modern product UI: a clear primary workflow, focused navigation, balanced spacing and consistent controls with visible state feedback.',
    'game': 'Genre-specific art direction: an immersive scene, deliberate atmosphere and a compact readable HUD; avoid marketing page layouts.',
}


def project_design_guidance(project_id: str, product_type: str | None = None) -> str:
    index = int.from_bytes(hashlib.sha256(project_id.encode()).digest()[:4], "big")
    direction = PURPOSE_DIRECTIONS.get(product_type, DESIGN_DIRECTIONS[index % len(DESIGN_DIRECTIONS)])
    return f"""
VISUAL DESIGN FOR THIS USER APPLICATION
Treat visual design as part of completing the requested application.
User-specified brand, colors, reference style and light/dark preferences take priority.
For a new app without a requested style, consider this project-specific starting direction:
{direction}
Adapt the direction to the app's purpose and audience; do not force it onto an established design.
The GeneSys builder's white-and-blue brand is not a default theme for generated apps.
Before editing, choose a coherent palette, typography, spacing, layout and shape language.
Use the persisted designStrategy as a design decision, not a rigid template. Evaluate
its alternatives against the user's audience, content, product and requested style.
Broaden composition beyond cards: editorial spreads, full-bleed scenes, split layouts,
curated galleries, task canvases, contextual drawers and progressive multi-view flows.
Choose a distinctive composition and at least one purposeful signature detail; avoid
defaulting every project to the same hero, three-card row and generic footer.
For redesign requests including 'build something different', inspect the current UI
and CSS, then change layout/section rhythm, typography and imagery treatment together.
Read both the current JSX structure and stylesheet before redesign edits. When edit_file
returns fresh currentContent after a mismatch, rebuild the patch from that source;
never repeat a stale old_text or guess closing JSX braces. Keep edits structurally complete.
Preserve working actions and saved data. A repair or a palette swap is insufficient.
Make the change visible in the actual rendered first screen and subsequent views.
Polish means appropriate composition and complete interaction states, not extra
gradients, animation or dependencies. Prefer subtle motion and fast, readable pages.
Implement them in the project's stylesheet using shared CSS variables for surfaces, text,
accents, borders, spacing and corners. Record the chosen direction in a CSS comment in that
same stylesheet edit, so subsequent requests can retain the design without an extra setup step.
On an existing app, inspect and reuse its visual tokens; change its theme only when requested.
Create a composed page with a clear focal point, useful information hierarchy, balanced density,
purposeful whitespace, polished typography and details appropriate to the requested product.
POLISH REQUIREMENTS FOR EVERY BUILD
Choose one visual concept suited to the product; modern does not mean adding gradients
or rounding every surface. Identify a distinctive focal point and compose around it.
Use a consistent type scale: large intentional page titles, clear section headings,
readable body copy with comfortable line length and quieter supporting labels.
Use an intentional spacing scale and shared container widths. Align controls, captions,
images and section edges; avoid arbitrary padding, competing shadows and uneven gaps.
Create hierarchy through composition, scale and contrast rather than a stack of
identical bordered cards. Use depth only where it clarifies structure.
Use concise, audience-appropriate copy in the user's language; no implementation
explanations, generic welcome paragraphs or developer controls in the main experience.
For a photographer portfolio the first screen should present photography and identity,
not a project-management sidebar, URL-entry forms or a CRUD dashboard. Put editing
tools in a separate accessible management view when needed, preserving their functions.
Give the portfolio a composed image hero, curated gallery rhythm, thoughtful image
crops, project captions, an about section and a clear contact action. Let photos occupy
substantial space. Choose images relevant to the stated photography genre; landscape
samples are unsuitable as the default for portraits, fashion, weddings or architecture.
Image order and aspect ratios should create a deliberate sequence, not repeated tiny
thumbnails. Preserve image proportions and legible caption placement on mobile.
For dashboards and tools, prioritize useful data and tasks; for games, prioritize the
playable scene. Do not decorate a tool with an oversized marketing hero.
Finish control styling, focus states, loading/empty/error states and mobile navigation.
Check the design at both desktop and phone widths; stack content intentionally and
keep important actions reachable without hover. Respect reduced motion.
Before ending implementation, perform a short polish pass within the same edit:
check visual hierarchy, spacing consistency, real imagery, copy, responsive composition
and whether the primary interaction is obvious. Do not sacrifice working functions.
For photographers' portfolios and other image-led sites, include actual photographic images
in the hero and gallery, not blank cards, gradients or icon substitutes. Use the user's provided
photos first. Without uploaded photos, use representative stock sample images, label the collection
as sample photography, and never claim these are the user's own photographs. For sample sources use
https://images.unsplash.com/photo-1500534623283-312aade485b7?auto=format&fit=crop&w=1200&q=80
https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80
https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80
Use descriptive alt text, responsive widths, aspect ratios, object-fit, and lazy loading below the fold.
Make image collections easy to replace with the user's real photos. Images must load in verification.
Images must depict their labeled subject and category: forest photos cannot represent cars;
sedans cannot represent SUVs. The landscape sample URLs above are for landscape photography,
never generic product placeholders. Do not infer photo contents from invented alt text.
If a matching photo's subject is unknown, use an accurate original SVG illustration, labeled
as an illustration, rather than an unrelated stock photo.
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
For branded websites create an original simple SVG logo, use it in the header and
as a favicon, and set a meaningful browser title. Avoid emoji as the finished brand.
Inspect both UI and handlers: exact payload keys, return shapes and dependent options
must agree. Scheduling selectors must populate available slots. Keep confirmations
visible after undo/toast timers expire; verify whole workflows rather than button visibility.
Give every form control a stable accessible name matching its visible label, using
explicit aria-label or label/htmlFor. Keep validation messages outside the label
and associate them with aria-describedby, so errors never change the input's name.
Do not use dead buttons, unrelated platform navigation or fake completed integrations.
Never implement Save as a no-op; render an editable form and persist its actual values.
Keep visible filter inputs synchronized with applied/reset state. Undo must remain
reachable after the deleted item and its detail view disappear. Give confirmation
actions distinct accessible names and use labeled dialogs/alertdialogs. Keep cards
as semantic articles/list items with real action buttons, not buttons containing buttons.
Use useEffect for timers and state side effects; useMemo only computes derived values.
For ordinary user-created app data, persist changes across reloads. Import the provided
usePersistentState hook from src/usePersistentState.js when present, use a stable descriptive
storage key, validate loaded data shape when needed and show storageError to the user.
Do not store secrets or passwords in browser storage. Browser storage is local to this
device; for shared multi-user data, require a real backend and database instead of claiming sync.
For an existing application, preserve its data keys and schema; do not discard saved data.
When browser verification is available, inspect the actual rendered application for layout,
readable content, clipping and the requested UI. A clean console alone is not visual proof.
"""
