# Booking calendar and availability recovery

The latest failing booking job guessed unavailable controls, then timed out while replanning. Source inspection also confirmed UTC/local calendar mismatch, stale slots after date changes, unreachable required-field validation, duplicate desktop navigation, and mobile navigation blocking Book.

The generic verifier now resolves bounded `{{date+0}}` through `{{date+30}}` against browser-local calendar dates without changing cached selectors. `chooseAvailable` clicks a real enabled visible option inside one named, bounded group; a separate outcome assertion is still mandatory. Live control inventory includes disabled state and excludes hidden/inert elements. Explicit local reservation creation and persistence are browser requirements; real payment integrations remain external.

The affected sandbox was backed up and repaired separately; no customer application source is part of this platform commit. Its exact production bundle passed all five browser requirements on 1440px and 390px in Europe/Riga, with no runtime errors. Checks cover discovery/back, future date and enabled slot selection, preserved review, required-field errors, contact confirmation, reservation reference persistence, cancellation confirmation and persisted cancellation. Payment remains an honestly labelled local demo.

Validation: 69 isolated release tests passed across schema, calendar/availability, contract scopes, verification plans, saved-source retry, canvas frames, continuous input, grounded diagnosis and workflow isolation. New helper tests also prove an availability action alone cannot satisfy a requirement.
