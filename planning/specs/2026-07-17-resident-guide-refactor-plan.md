# Resident Guide Refactor Plan

**Date:** 2026-07-17

**Area:** Resident Guide sections/navigation (“resident tabs”), content dispatch, and build-time content boundary

**Status:** Planning only

**Security gate:** Begin only after the audit's four Medium findings are closed or explicitly accepted.

## Interpretation and outcome

“Resident tabs” is interpreted as the routeable Resident Guide section navigation in `Guide.svelte`: a desktop sidebar that becomes a horizontal section strip on narrow screens.

The outcome is a smaller guide shell with explicit navigation and content contracts, safer build-time HTML handling, and reliable deep links—without turning the guide into a generic tab widget or redesigning its civic visual identity.

## Current review

- `src/lib/Guide.svelte` is 205 physical lines and combines guide loading, active-section selection, navigation/footer actions, responsive layout, offline-badge policy, and lightbox ownership.
- `src/lib/guide/GuideSection.svelte` is a clear but growing conditional dispatcher for Markdown and six specialized widget types.
- The bundle has runtime validation and real-file tests, but nested validation is uneven and section IDs/content keys are not treated as a fully cross-referenced schema.
- Markdown is converted to HTML at build time and rendered with `{@html}`. The source is tracked/trusted and links are scheme-validated, so this is not a current resident-input XSS vulnerability. The trust contract should still fail closed before more content authors or sources are added.
- Click-to-load video, on-device content, section icons, typed callouts, lightbox behavior, and specialized offline badges are good patterns to preserve.

## Navigation decision

Use `<nav>` with buttons/links and `aria-current`, not `role="tablist"`/`role="tab"`.

The sections are addressable routes (`#guide/<id>`), work with browser history, and become sidebar navigation on desktop. ARIA tabs imply a single tab panel and a specific roving-focus interaction that does not accurately describe this responsive route navigation. The plan will still add predictable arrow-key scrolling/focus as an enhancement on the horizontal mobile strip if user testing supports it.

## Approach decision

- **Shell/nav/content separation — recommended.** Keep the bundle format and specialized widgets; extract navigation and make dispatch exhaustive.
- **One route/component per section.** Rejected for now: it fragments a compact offline bundle and duplicates loading/error behavior.
- **External CMS-driven guide.** Rejected for this phase: it creates a new untrusted HTML/data boundary and operational dependency.

## Target ownership

```text
Guide.svelte
  owns bundle load state, active route, lightbox, and high-level layout
  -> guide/GuideNav.svelte
       owns section navigation, aria-current, About/PDF actions, responsive focus
  -> guide/GuideContent.svelte
       owns heading, offline-badge policy, and exhaustive section renderer
       -> existing specialized resident widgets

tools/build_guide.mjs
  owns trusted Markdown conversion and output validation
guide/guideBundle.ts
  owns the complete runtime cross-reference contract
```

## Implementation sequence

### Phase G1 — Strengthen the guide bundle contract

**Files:** modify `src/lib/guide/guideBundle.ts`; extend `test/guideBundle.test.ts`; review `src/lib/types.ts`.

Validate the complete bundle rather than just the outer shapes:

- section IDs are non-empty, URL-safe, and unique;
- titles, types, icons, provider/src fields, and required type-specific fields are valid;
- every Markdown section has a string entry in `content` and no orphan content key exists;
- specialized sections have the required contacts/meetings/widget data;
- external PDF/video/link schemes are allowed and expected hosts can be constrained where appropriate;
- contact/meeting arrays validate every item, not only representative fields;
- the first section is always a valid fallback.

Run the validator against the real generated `public/guide.json` in tests.

**Exit:** A malformed or internally inconsistent guide fails with a section ID and field path before rendering.

### Phase G2 — Make the Markdown-to-HTML trust boundary fail closed

**Files:** modify `tools/build_guide.mjs`; extend `test/guide-callouts.test.ts` or add a dedicated guide HTML test.

Choose and document one policy:

1. Preferred: sanitize generated HTML with a small audited allowlist of the exact tags/attributes the guide uses.
2. Acceptable if raw HTML is unnecessary: reject raw HTML in Markdown and generate only renderer-owned HTML/callouts.

In either case:

- reject event-handler attributes, `style`, scripts/iframes/objects, unsafe URL schemes, protocol-relative destinations, and unexpected data attributes;
- allow only the image/link attributes needed by the lightbox and external links;
- preserve the click-to-load video component rather than permitting Markdown embeds;
- add malicious fixtures covering `javascript:`, `data:text/html`, encoded schemes, raw `<script>`, `onerror`, and malformed tags;
- keep all content generation at build time; do not introduce runtime Markdown parsing.

**Exit:** The build fails on prohibited content and the current 20-section guide renders unchanged.

### Phase G3 — Extract routeable guide navigation

**Files:** create `src/lib/guide/GuideNav.svelte`; modify `src/lib/Guide.svelte`; add navigation-focused tests where practical.

Move section list, active styling, About action, PDF link, and responsive navigation styles together. The component receives sections/active ID and emits `onSelect(id)`; it must not import the global store.

Accessibility requirements:

- label the nav “Resident Guide sections”;
- expose the current section with `aria-current="page"`;
- preserve native Tab behavior and 48-pixel mobile touch targets;
- scroll the current item into view on mobile route changes without unwanted motion when reduced motion is enabled;
- keep About and PDF actions visually distinct from section routes;
- preserve focus during Back/Forward navigation and after layout breakpoint changes.

**Exit:** `Guide.svelte` contains no section-nav markup or nav styles.

### Phase G4 — Extract guide content composition

**Files:** create `src/lib/guide/GuideContent.svelte`; modify or replace `GuideSection.svelte`; retain specialized widgets.

Move the active heading, generic/specialized offline-badge decision, and section dispatch into one content composer. Use an exhaustive TypeScript discriminated union or explicit switch so a newly added section type fails at compile/test time until its renderer is registered.

Keep these domain-specific components independent: Contacts, Meetings, Waste Schedule, Operations Status, CivicClerk Meetings, and Video. Do not wrap each Markdown section in a new component.

The content component receives `section`, `bundle`, and `openImage`; it does not read route/store state.

**Exit:** `Guide.svelte` owns load/route/lightbox/layout only; new section types have one obvious registration point.

### Phase G5 — Deep-link and resident-task verification

Extend route tests for:

- bare `#guide` selects the first valid section;
- every `#guide/<id>` direct link selects the matching section;
- unknown/deleted IDs fall back predictably and normalize the route without a loop;
- encoded or malformed IDs never select arbitrary content;
- Back/Forward restores section and focus appropriately;
- a guide anchor inside Markdown does not collide with the section route;
- offline badge appears once, including self-badged Waste and CivicClerk sections;
- lightbox open/close and Android hardware Back remain correct;
- PDF and external links use safe destinations and `noopener noreferrer`;
- video causes no third-party request until the resident activates it.

Conduct a content-oriented visual review at desktop, tablet, and narrow phone widths. Preserve the guide's “resident task spine”: recognizable City sections, strong active wayfinding, readable callouts, comfortable line length, and direct official-source links. Structural refactoring must not become a generic dashboard/card redesign.

## File-level deliverable

| File | Planned result |
|---|---|
| `src/lib/Guide.svelte` | Load/route/lightbox/layout shell, roughly 80–120 lines including shell styles |
| `src/lib/guide/GuideNav.svelte` | Routeable responsive section navigation and footer actions |
| `src/lib/guide/GuideContent.svelte` | Heading, offline policy, exhaustive content dispatch |
| `src/lib/guide/guideBundle.ts` | Complete runtime schema and cross-reference validation |
| `tools/build_guide.mjs` | Explicit fail-closed HTML policy |
| Guide tests | Real-bundle schema, malicious HTML fixtures, routes, offline policy |

## Verification and rollback

Run after each phase:

```powershell
npm run guide
npm run check
npm test
npm run build
```

The guide build regenerates `public/guide.json`; review its diff and confirm it contains no unintended content or broad formatting churn. Keep schema/security, navigation, and content-composer work in separate commits. If sanitization changes current output, review each change with the content owner instead of silently weakening the policy. Do not combine this plan with map or dashboard edits.
