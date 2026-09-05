---
name: Ledger Balance
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45464d'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#006398'
  on-secondary: '#ffffff'
  secondary-container: '#5bb8fe'
  on-secondary-container: '#00476e'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#271901'
  on-tertiary-container: '#98805d'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#cce5ff'
  secondary-fixed-dim: '#93ccff'
  on-secondary-fixed: '#001d31'
  on-secondary-fixed-variant: '#004b73'
  tertiary-fixed: '#fcdeb5'
  tertiary-fixed-dim: '#dec29a'
  on-tertiary-fixed: '#271901'
  on-tertiary-fixed-variant: '#574425'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  body-default:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
  body-medium:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
    letterSpacing: 0em
  body-xs:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: 0.01em
  label-mono-sm:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: -0.02em
  label-mono-xs:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
    letterSpacing: -0.01em
  metric-display:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  spacing-2xs: 2px
  spacing-xs: 4px
  spacing-sm: 8px
  spacing-md: 12px
  spacing-base: 16px
  spacing-lg: 20px
  spacing-xl: 24px
  spacing-2xl: 32px
  row-height-compact: 32px
  row-height-standard: 40px
  sidebar-width: 240px
  drawer-width-md: 480px
  drawer-width-lg: 640px
---

## Brand & Style
This design system is engineered for mission-critical enterprise reconciliation, ledger audit, and treasury automation. The aesthetic prioritizes absolute data legibility, high scanning velocity, emotional stability, and operational precision. It evokes the confidence of double-entry bookkeeping merged with modern enterprise ergonomics.

Key brand and stylistic tenets:
- **Zero Decorative Noise:** Strictly zero non-functional gradients, blurred glassmorphism, decorative glows, or whimsical icons. Every pixel serves auditability and spatial orientation.
- **Architectural Utility:** A clean, structural visual language utilizing 1px borders, subtle tonal divisions, and dense tabular grids. Data is the visual foreground; the interface is the structural chassis.
- **Controlled Interaction:** High contrast interactive states achieved through deliberate stroke color shifts, quiet surface hover tints, and keyboard-first affordances. Focus states use crisp, offset single-ring outlines.

## Colors
The color architecture enforces a high-density, low-fatigue workspace. Background surfaces alternate between clinical whites (`#FFFFFF`) and subdued container slates (`#F8FAFC`, `#F1F5F9`).

### Palette Tokens & Roles
- **Primary Surface / Brand (`#0F172A`):** Deep charcoal slate used for primary solid action buttons, key metrics, and dominant typography.
- **Interactive Accent (`#0284C7`):** Precision sky-slate accent reserved exclusively for links, active tab underlines, focus rings, selected table states, and secondary action affordances.
- **Neutral Hierarchy:**
  - Headings & Primary Data: `#0F172A`
  - Body Text & Secondary Identifiers: `#334155`
  - Meta Labels & De-emphasized Data: `#64748B`
  - Placeholders & Subtle Glyphs: `#94A3B8`
  - Active Borders & Table Separators: `#CBD5E1`
  - Passive Surface Borders & Outlines: `#E2E8F0`
  - Table Alternating Rows & Input Backgrounds: `#F8FAFC`
  - Base Viewport Background: `#F1F5F9`
  - Surface Card & Drawer Background: `#FFFFFF`

### Semantic Status Tokens
Status indicators employ desaturated, muted background fills accompanied by structured 1px perimeter borders and dark, high-contrast foreground text to preserve WCAG AAA compliance:
- **Matched / Reconciled:** Background `#ECFDF5`, Text `#065F46`, Border `#A7F3D0`
- **Review / Under Investigation:** Background `#FFFBEB`, Text `#92400E`, Border `#FDE68A`
- **Exception / Unmatched / Break:** Background `#FEF2F2`, Text `#991B1B`, Border `#FECACA`
- **Neutral / Draft / Archived:** Background `#F1F5F9`, Text `#475569`, Border `#E2E8F0`

## Typography
The typographic system delivers clear hierarchy under extreme information density. 

- **Primary Font Family:** Inter is configured with `font-feature-settings: "cv02", "cv03", "cv04", "cv11", "tnum" 1;` across all table columns, currency instances, and ledger metrics to prevent optical jitter during balance scans.
- **Monospaced Utility:** JetBrains Mono is assigned to raw ledger hashes, UTR IDs, payment gateway references, system timestamps, and API response payload payloads.
- **Dense Sizing Scale:** Standard enterprise desktop text lives at `13px` (with `18px` line height). Table cells, badges, and inline status markers throttle down to `12px` and `11px`.
- **Currency & Metric Rules:** Financial amounts (e.g., INR values like `₹1,42,85,910.42`) must mandate `font-variant-numeric: tabular-nums` and right-aligned cell layouts.

## Layout & Spacing
This design system uses a strict 4px grid system optimized for horizontal real estate, enabling analysts to view extensive ledger attributes without vertical scrolling.

### Layout Philosophy
- **Fixed Sidebar + Fluid Content:** A non-collapsible, compact 240px navigation shell paired with an edge-to-edge fluid main workview constrained only by a maximum width of `1680px` on ultrawide monitors.
- **Multi-Split Workspace:** Dual-pane and drawer-integrated views allowing reconciliation matching: Left panel for Source of Truth (Core Banking/Internal Ledger), Right panel for Settlement Gateway (Razorpay/Stripe/NPCI), and sliding overlays for rule match confidence breakdown.
- **Row Heights:** Table rows maintain an uncompromising standard: 32px for compact mode (dense manual reconciliation queues) and 40px for standard inspection mode (detailed review).
- **Responsive Adaptations:**
  - Desktop (`> 1280px`): Full table views with up to 12 visible columns, persistent filters, and right-side collapsible split drawers.
  - Tablet / Laptop (`1024px - 1279px`): Sticky leftmost transaction identifier columns, horizontally scrollable metadata columns, and modal-based side audit sheets.
  - Breakpoint limits (`< 1024px`): Not supported for standard reconciliation workflows. Enterprise users receive a read-only responsive fallback queue.

## Elevation & Depth
Elevation is rendered strictly via tonal surface borders (`#E2E8F0` and `#CBD5E1`) and minimal, diffused contact shadows.

- **Level 0 (Canvas Base):** `#F8FAFC`. Background for application margins and gutter spacing.
- **Level 1 (Structural Containers):** `#FFFFFF`. Worklist tables, KPI card decks, and filter ribbons. Outlined with `1px solid #E2E8F0`. No shadow.
- **Level 2 (Interactive Floating Elements):** Dropdown menus, popover date selectors, and auto-suggest search lists. Surface: `#FFFFFF`, Border: `1px solid #CBD5E1`, Shadow: `0 4px 12px -2px rgba(15, 23, 42, 0.06), 0 2px 4px -1px rgba(15, 23, 42, 0.04)`.
- **Level 3 (Overlay Surfaces):** Slide-out audit trail drawers and discrepancy inspection sheets. Surface: `#FFFFFF`, Border-left: `1px solid #CBD5E1`, Shadow: `-8px 0 24px -4px rgba(15, 23, 42, 0.08)`. Backdrop utilizes a flat slate dim: `rgba(15, 23, 42, 0.3)`.

## Shapes
Shapes emphasize precision and utility through low corner radiuses. 

- **Corner Radius Scale:**
  - Base input elements, select triggers, table cells, and buttons: `4px` (`rounded-sm`).
  - Cards, modal containers, and drawers: `6px` to `8px` (`rounded-md`).
  - Semantic status pills: `4px` (avoids organic pill capsules in favor of compact, blocky tags for tighter horizontal table stacking).
- **Outlines and Strokes:** Standardized stroke width is `1px` across all containers, inputs, dividers, and tables. No 2px or heavy brutalist borders.

## Components

### 1. Data Tables
- **Header:** Height of 32px, surface `#F8FAFC`, bottom border `1px solid #E2E8F0`. Typography: `11px`, `600` weight, uppercase, `#64748B`, with sort direction glyphs rendered inline in `#94A3B8`.
- **Rows:** Alternating rows inactive by default; pure `#FFFFFF` background with `1px solid #F1F5F9` bottom divider. Hover background transitions instantaneously to `#F8FAFC`. Selected match candidate highlights with `#F0F9FF` background and `#BAE6FD` border.
- **Cells:** Padding `6px 12px`. Numerical and currency values strictly right-aligned with `tabular-nums`.

### 2. Status Badges & Chips
- Displayed with a compact `18px` fixed height, `4px` radius, padding `0 6px`.
- Styled with `11px` medium font, accompanied by a 6px solid circular status dot indicator pinned to the left:
  - *Matched:* Background `#ECFDF5`, Dot `#10B981`, Text `#065F46`, Border `#A7F3D0`.
  - *Under Review:* Background `#FFFBEB`, Dot `#F59E0B`, Text `#92400E`, Border `#FDE68A`.
  - *Break / Unmatched:* Background `#FEF2F2`, Dot `#EF4444`, Text `#991B1B`, Border `#FECACA`.

### 3. Metric & KPI Cards
- Background `#FFFFFF`, border `1px solid #E2E8F0`, padding `12px 16px`.
- Structure: Subdued title (`12px`, `#64748B`), large balance metric (`20px`, `600`, `#0F172A`, `tabular-nums`), and inline baseline delta badge (`11px` green/red pill indicating day-over-day variance).

### 4. Buttons & Controls
- **Primary:** Background `#0F172A`, text `#FFFFFF`, hover `#1E293B`, active `#020617`. Height: 32px.
- **Secondary / Outline:** Background `#FFFFFF`, border `1px solid #CBD5E1`, text `#334155`, hover `#F8FAFC`.
- **Segmented Control:** Enclosed container `#F1F5F9`, active segment `#FFFFFF` with `0 1px 2px rgba(0,0,0,0.05)` and `1px solid #CBD5E1`.

### 5. Input Fields & Search
- Height 32px. Background `#FFFFFF`, border `1px solid #CBD5E1`, text `#0F172A`, placeholder `#94A3B8`.
- Focused state: border color `#0284C7` with box-shadow `0 0 0 1px #0284C7`. No excessive blur or outer halos.

### 6. Audit Trail & Rule Breakdown Drawer
- Persistent side pane (`480px` width) for comparing discrepancies side by side.
- Displays line-by-line field reconciliation (e.g., Merchant Order Amount vs. Settlement Net Amount), highlighting difference rows in red tint (`#FEF2F2`) with monospace difference figures.