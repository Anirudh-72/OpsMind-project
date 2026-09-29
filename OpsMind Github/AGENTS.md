# AGENTS.md — OpsMind Engineering Rules

## Product scope
- Build only the OpsMind MVP described in the project prompt.
- Do not add unrequested features.
- Do not create a generic marketing landing page.
- Do not build a fake dashboard full of decorative statistics.
- Prioritize the working incident investigation flow.

## Visual restrictions
- Never use purple, indigo, violet, neon cyan, or magenta gradients.
- No glowing borders or blurred background blobs.
- No glassmorphism.
- No nested cards or excessive rounded containers.
- Maximum panel border radius: 6px.
- Maximum button/input border radius: 4px.
- Avoid heavy decorative shadows.
- Use hairline borders and clear information hierarchy.
- No emojis anywhere in the UI.
- Do not add decorative AI badges above every heading.
- Do not create generic three-column feature-card layouts.
- Use icons only when they improve navigation or status clarity.
- Do not add icons or buttons that do nothing.

## Typography
- Use Geist, Plus Jakarta Sans, or a similar clean UI font.
- Use JetBrains Mono or IBM Plex Mono for incident IDs, timestamps, technical identifiers, and metrics.
- Use tabular numbers for numerical data.
- Keep dense technical information readable and aligned.

## Interaction integrity
- Every visible button, input, tab, filter, and dropdown must work.
- If a feature is not implemented, do not show its control.
- Every asynchronous action must have loading, success/populated, empty, and error states where applicable.
- Forms must validate input.
- Forms must support Enter-key submission.
- Display clear feedback after important actions.
- Never silently swallow errors.

## Data integrity
- Do not use John Doe, Lorem Ipsum, Acme Corp, or meaningless placeholder statistics.
- Use believable fictional incident records.
- Clearly label fictional sample data.
- Never present generated hypotheses as confirmed facts.
- Never claim a fix is verified unless the sample record or user explicitly marks it verified.

## Code quality
- Separate data access, memory integration, LLM logic, and UI components.
- Keep design tokens centralized in CSS variables.
- Do not duplicate business logic across components.
- Keep API keys server-side.
- Avoid unnecessary dependencies.
- Do not rewrite working backend logic while restyling the frontend.
- Explain important architectural decisions in the README.
