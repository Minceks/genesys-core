# Product-aware design

Before implementation the backend classifies game, portfolio, store, dashboard, app, or website,
and saves `.genesys-design.json` inside the user project. It adds no model planning call.
The brief guides layout, assets, interaction and technical choices and is shared with parallel workers.
Follow-up edits retain the direction; explicit requests for a different product purpose replace it.
User color/style/reference preferences override default recommendations.
Classification uses keyword rules and is approximate; ambiguous requests retain the previous type,
or start as website. Brief verification checks are model requirements, not newly automated tests.
Existing build, browser runtime, visual and content checks remain responsible for verification.
