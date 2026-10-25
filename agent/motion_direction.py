"""Conditional art, asset and motion handoff for generated products."""

import re


def motion_direction(brief):
    request = str(brief.get('originalRequest') or '').lower()
    cinematic = bool(re.search(r'\b(cinematic|scrollytelling|scroll[- ]cinematic|image[- ]sequence|exploded view)\b', request))
    return {
        'mode': 'cinematic-candidate' if cinematic else 'purposeful-interface',
        'selection': 'Use cinematic chapters only when the requested story benefits. Preserve existing scope on repairs. Apps, dashboards and forms prioritize task speed and readable state; never impose a luxury dark theme or scroll hijacking.',
        'artDirection': 'Choose a subject-specific focal image, intentional type pairing, negative space and section rhythm. Carry the same identity through all destinations and states. Avoid repetitive card grids when editorial composition better fits the content.',
        'assetContract': [
            'Inventory required hero/detail assets, available files, dimensions, identity anchors, provenance/license and loading fallback before implementation. Use actual subject imagery or a clearly identified original illustration; no empty media placeholders or invented product facts.',
            'For generated variations, reuse an approved anchor/reference to preserve product identity. Use only available authorized providers and remaining budget. Missing video generation is an explicit limitation: choose a finished static composition instead of claiming clips were generated.',
            'Keep assets project-local when permitted. Confirm files decode and record actual dimensions, frame count and byte size before using them. Pin optional library versions and report actual generation usage; do not invent credits spent.',
        ],
        'motionContract': [
            'Prefer CSS and native scrolling for ordinary transitions. Motion must explain hierarchy, navigation or state and leave content and controls usable without animation.',
            'For an approved image-sequence story, map clamped section progress deterministically to frame indices; reverse progress reuses the same frames. Use a sticky canvas, cover-fit drawing, device-pixel-ratio cap, resize handling and requestAnimationFrame; draw only when the frame or canvas size changes. Clean up listeners, observers and animation callbacks.',
            'Measure asset bytes and decoded memory before choosing resolution/frame count. Load the poster and initial frames first, then a bounded neighboring-frame window with bounded concurrency and eviction. Never preload hundreds of full-resolution frames or lock all navigation behind a global loader.',
            'Handle failed frames, image decode failure and stalled loading with a visible poster and retry or skip control. Progress counts settled requests honestly; failure must never become a permanent black loading screen.',
            'Respect prefers-reduced-motion and data-saving preferences: show a static meaningful poster with all text/actions available. On phone choose a lighter static or user-controlled video treatment; autoplay is optional, muted and playsinline with rejected-play fallback. Do not replace reduced motion with a looping video.',
            'Keep semantic headings, readable DOM copy and keyboard-accessible actions outside canvas. Decorative canvas/media is hidden from assistive technology; essential diagrams need an equivalent description. Callouts must remain legible without pinning or animation.',
        ],
        'evidence': [
            'When implemented, exercise forward and reverse scroll at multiple positions and confirm visible frame changes, resize behavior and readable callouts. Screenshots alone do not prove scrubbing or smoothness.',
            'Test desktop, phone, reduced motion, failed media and blocked autoplay. Confirm content/actions remain reachable, loading can recover and no new console errors occur. Report checks actually run, unavailable assets and performance measurements separately; do not claim 60fps or award-level quality without evidence.',
        ],
    }
