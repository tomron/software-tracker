## ADDED Requirements

### Requirement: Static HTML/JS dashboard served on GitHub Pages
The dashboard SHALL be a single `docs/index.html` file with accompanying assets in `docs/assets/`. Individual project pages SHALL be at `docs/projects/<slug>.html` or rendered client-side from `index.html` using URL hash/query routing. It SHALL be served by GitHub Pages from the `docs/` directory of the main branch. No build step is required.

#### Scenario: Dashboard loads without a build step
- **WHEN** GitHub Pages serves `docs/index.html`
- **THEN** the page renders correctly using only static files; no server-side rendering or compilation is required

#### Scenario: Dashboard readable without JavaScript
- **WHEN** JavaScript is disabled in the browser
- **THEN** the page displays a meaningful static fallback or message rather than a blank screen

---

### Requirement: Project data loaded from JSON files
The dashboard SHALL fetch per-project data from `docs/data/<slug>.json` at runtime using the Fetch API. A `docs/data/index.json` manifest file SHALL list all project slugs and their display names so the index page can discover projects without hardcoding.

#### Scenario: Project data loaded successfully
- **WHEN** the page loads and `docs/data/<slug>.json` exists
- **THEN** the dashboard renders that project's summary, Q&A answers, breaking-change status, and alternatives

#### Scenario: Project data file missing
- **WHEN** `docs/data/<slug>.json` does not exist or returns a 404
- **THEN** the dashboard shows a "not yet tracked" placeholder for that project

---

### Requirement: Project index page
The dashboard index (`docs/index.html`) SHALL show a card grid of all tracked projects, each card linking to the full project detail view. The index SHALL be the primary entry point and work as a standalone overview.

Each project card SHALL display: display name, description, category tags, last-run timestamp, and a breaking-change badge if applicable.

#### Scenario: Index lists all projects
- **WHEN** the index page loads
- **THEN** one card is rendered per entry in `docs/data/index.json`

#### Scenario: Project card links to detail view
- **WHEN** the user clicks a project card
- **THEN** the browser navigates to the project detail view (either a separate page or a hash-routed view)

#### Scenario: Breaking change badge on index card
- **WHEN** a project has `breaking_changes: true`
- **THEN** its index card shows a prominent warning badge

---

### Requirement: Per-project detail view
Each project detail view SHALL display: display name, description, homepage and repo links, categories, last-run timestamp, full summary, Q&A answers table, breaking-change indicator with excerpts, and alternatives list. A breadcrumb or back link SHALL return the user to the index.

#### Scenario: Breaking change present
- **WHEN** `breaking_changes` is `true` in the project data
- **THEN** a visible warning indicator is shown, alongside the breaking excerpts

#### Scenario: Q&A answers displayed
- **WHEN** the project has one or more answered questions
- **THEN** each question and its answer are shown in a table or list

#### Scenario: Alternatives displayed
- **WHEN** the project data contains one or more alternatives
- **THEN** each alternative is shown with its name, review text, and URL (if present); config-sourced and LLM-discovered alternatives are both shown

---

### Requirement: Category filtering on index
The index page SHALL allow filtering the project card grid by category tag. All active category tags SHALL be shown as clickable chips above the grid.

#### Scenario: Category filter applied
- **WHEN** the user clicks a category chip
- **THEN** only project cards with that category are shown; the active chip is visually highlighted

#### Scenario: Multiple categories selected
- **WHEN** the user clicks more than one category chip
- **THEN** projects matching any selected category are shown (OR logic)

#### Scenario: No category filter active
- **WHEN** no category chip is selected
- **THEN** all project cards are displayed

---

### Requirement: Dark and light mode
The dashboard SHALL support both dark and light color schemes. The default SHALL follow the user's OS/browser preference via the `prefers-color-scheme` CSS media query. A toggle button SHALL allow the user to manually switch modes, with the preference persisted in `localStorage`.

#### Scenario: OS preference respected on first load
- **WHEN** the user visits the dashboard for the first time with no stored preference
- **THEN** the color scheme matches the OS/browser `prefers-color-scheme` setting

#### Scenario: Manual toggle persisted
- **WHEN** the user clicks the dark/light mode toggle
- **THEN** the scheme switches immediately and the choice is saved to `localStorage` so it persists on next visit

#### Scenario: Dark mode contrast
- **WHEN** dark mode is active
- **THEN** all text, badges, and UI elements maintain sufficient contrast (WCAG AA minimum)

---

### Requirement: Responsive mobile-first layout
The dashboard SHALL render correctly and be fully usable on mobile screens (320px and above) as well as desktop. Layout SHALL use CSS flexbox or grid with responsive breakpoints. Touch targets SHALL be at least 44×44px.

#### Scenario: Mobile card grid
- **WHEN** the viewport width is less than 640px
- **THEN** project cards are displayed in a single-column layout with adequate spacing

#### Scenario: Desktop card grid
- **WHEN** the viewport width is 640px or wider
- **THEN** project cards are displayed in a multi-column grid (2–4 columns depending on width)

#### Scenario: Navigation usable on touch
- **WHEN** a user navigates on a touch device
- **THEN** all interactive elements (cards, filter chips, toggle, links) are easily tappable with no overlap

---

### Requirement: Modern visual design
The dashboard SHALL use a clean, modern visual style: a consistent type scale, adequate whitespace, subtle shadows or borders to separate cards, and a cohesive color palette that works in both dark and light modes. No external CSS framework is required; styles SHALL be written in plain CSS.

#### Scenario: Consistent typography
- **WHEN** the page renders
- **THEN** headings, body text, and labels use a consistent type hierarchy with a system font stack or a single self-hosted font

#### Scenario: Cards visually distinct
- **WHEN** multiple project cards are shown in the grid
- **THEN** each card has a visible boundary (border or shadow) and sufficient internal padding to be easily scannable

---

### Requirement: Pipeline writes data to docs/
After each run the pipeline SHALL write `docs/data/<slug>.json` with the same content as `data/<slug>/latest.json`, and SHALL update `docs/data/index.json` with the current list of all project slugs and their display names.

#### Scenario: docs/data updated after run
- **WHEN** the pipeline completes processing a project
- **THEN** `docs/data/<slug>.json` is created or overwritten with the latest output before the commit

#### Scenario: index.json kept in sync
- **WHEN** the pipeline runs (for any project or all projects)
- **THEN** `docs/data/index.json` is regenerated to reflect all currently tracked projects
