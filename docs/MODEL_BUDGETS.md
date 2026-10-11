# Model context limits

Screenshot binary/hex and inline image data are omitted from text repair prompts.
Screenshots remain available as browser artifacts; dimensions, URL and errors remain in context.
`GENESYS_INPUT_TOKEN_LIMIT` defaults to 24000 estimated input tokens, including tools and a margin.
Groq has an additional 4000-token input cap. These are per-call limits, not per-user spending limits.
`GENESYS_OUTPUT_TOKEN_LIMIT` defaults to 6000 output tokens for OpenAI, bounded between 2000 and 12000.
Token estimates use o200k_base; provider billing tokenizers may differ.
Over-budget conversations retain the initial instructions/request and recent work, shortening older content.
Truncated source is marked so the agent can read the current file before changing it.

Photography portfolio guidance requires user photos or labeled stock sample images, descriptive alt text,
responsive sizing, and replaceable sources. Browser verification checks loaded hero/gallery photos and
reports missing/broken images as repair failures. External sample-photo availability is not guaranteed.
