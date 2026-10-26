"""Concrete senior engineering decisions shared by builders and reviewers."""

SENIOR_ENGINEERING_STANDARD = '''SENIOR PRODUCT ENGINEERING
Own the outcome like a senior developer and product designer: understand the actual
audience, primary journey and constraints, inspect the real architecture, compare
viable approaches, and choose the simplest maintainable implementation that fully
serves the request. Build coherent components and data contracts, not isolated demos.
Use engineeringStrategy and trendIntelligence in the saved brief. Ground any trend
adaptation in dated relevant evidence and explain why it fits; choose zero when it
does not. User requirements and explicit references take precedence over trends.
Current discovery listings are signals, not proof that a visual style is trending.
For targeted fixes preserve the product, theme, dependencies and saved data; do not
redesign or expand scope because research changed. For full products compose an
original identity and complete the selected end-to-end journey. Prioritize usable
phone layouts, accessibility, performance, honest integrations and recoverable states.
Keep reasoning concise in the implementation plan. Finish JSX, CSS, assets and actions
together, then exercise real workflows and inspect rendered desktop/phone output.
Compilation, functional tests and visual review are separate evidence. Never invent
test results, market leadership, security guarantees or completed external operations.
'''

PATTERNS = {
    'website': ['Content-led composition and a clear primary destination', 'Distinctive typography with restrained purposeful motion', 'Useful detail pages and a composed phone reading flow'],
    'portfolio': ['Large original work with varied project scale', 'Substantial case-study storytelling', 'Minimal navigation that lets the work lead'],
    'store': ['Editorial product storytelling and useful discovery', 'Clear detail, comparison and buying decisions where relevant', 'Continuous saved basket and honest checkout handoffs'],
    'dashboard': ['Task-led data density and progressive drill-down', 'Contextual filters, meaningful visualizations and record detail', 'Readable empty, loading, error and populated states'],
    'app': ['A focused primary workflow with progressive disclosure', 'Contextual actions and reliable saved state', 'Fast feedback and deliberate mobile navigation'],
    'game': ['A readable genre-specific world and immediate playable feedback', 'Legible HUD, onboarding and keyboard/touch controls', 'A coherent core loop, pause/restart and truthful saved progression'],
}


def engineering_strategy(brief, prompt, trends):
    from .design_strategy import requests_redesign
    from .trend_intelligence import trend_refresh_requested
    targeted = brief.get('buildIntent') == 'edit-product' and not (requests_redesign(prompt) or trend_refresh_requested(prompt))
    return {'version':1,'role':'Senior product engineer and lead interface designer',
            'mode':'preserve-and-repair' if targeted else 'design-and-build',
            'objective':str(brief.get('originalRequest') or prompt)[:1200],'currentRequest':prompt[:1200],
            'trendEvidenceStatus':trends.get('status','curated-fallback'),
            'candidatePatterns':[{'pattern':item,'basis':'Curated product-fit recommendation; not a measured popularity claim.'}
                                 for item in PATTERNS.get(brief.get('productType'),PATTERNS['website'])],
            'decisionContract':{'audience':'Identify the real user, primary task and success outcome from the request.',
                'constraints':'Honor explicit style, genre, single-page/minimal scope, data ownership, available assets and dependencies.',
                'alternatives':'Compare two practical approaches in a few sentences; choose for fit, implementation cost and maintainability.',
                'trendAdaptation':'Select zero to three relevant ideas, recording source/date or curated basis, expected user benefit and rejected mismatches.',
                'architecture':'Choose component boundaries, state/data contracts and real integration needs before implementation.',
                'scope':'Preserve existing design, workflows and stored data; repair only the requested behavior.' if targeted else 'Complete the requested product journey; optional trend ideas are candidates, not added requirements.'},
            'deliveryOrder':['Inspect the actual project and identify acceptance outcomes',
                'Choose a coherent product-specific direction using relevant evidence',
                'Implement the full selected workflow, responsive styling and real assets together',
                'Verify normal, invalid, empty, failure and recovery states through real inputs',
                'Report what passed and what remains unavailable or unverified'],
            'qualityPriorities':['Working core workflow before decoration','Accessible stable controls and intentional phone layout',
                'Bounded assets/motion and respect for reduced motion','Maintainable modules and preserved data contracts',
                'Evidence from actual rendered output; no fabricated integration or popularity claims']}
