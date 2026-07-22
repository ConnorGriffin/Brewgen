# Issue #26 — locked visual direction (grilling session, 2026-07-21)

Direction agreed with Connor via rendered sketches. This supersedes all prior
result concepts (radar cards, sensory map, comparison lens, matrix R3 — all
rejected). Build the next HTML prototypes to this spec; deviations need a new
decision.

## Visual language

- **Editorial brew-book × tactile malt.** Warm cream (#faf6ec-family), dark
  ink, amber, restrained rosewood. Serif (Georgia-class) for display numerals,
  grain-bill letters, and percentages; quiet sans for labels.
- **The malt stack is the hero.** Each grain bill renders as vertically
  stacked layers; layer color derives from the malt's real Lovibond, layer
  height from its percentage. No bar charts, no radar, no grid tables.
- **Pour band.** Below each stack, a full-width band tinted to that bill's
  estimated beer color, containing only "8.2 SRM · 5.5% ABV" (serif). No
  "pours at" label or similar copy — rejected as cheesy.
- Exact percentages in a dot-leader list under the stack, with small malt
  color swatches.
- Differentiators ("most malty") are sparse italic serif asides next to the
  letter — never badge pills.

## Results screen

- **Shelf composition:** all grain bills (2–5) visible at once as full cards
  in one row. No ranking, letters only.
- **Selection = spines:** selected card expands in place; the others compress
  to thin labeled spines (letter + mini malt stack) that remain tappable.
  Comparison never leaves the screen.
- **Mobile:** no swipe deck, no vertical list. Phone starts directly in the
  spines state (one bill open, others as flanking spines). Verified legible
  at 375px with 5 bills (~220px open card).
- **Brief header:** the brief read back as short flat serif sentences,
  order-ticket style: "American Pale Ale. Malty and honeyed, no coffee.
  About 5.5%, amber-gold." Underlined terms, small "edit brief" action.
  No em-dashes, no generated-copy tone. Not a dark ink bar, not chips.

## Input screen (brief construction)

- **Quiet form** (option 2, not the madlib): stacked controls on cream —
  style dropdown, strength slider with % readout, color slider whose track
  is a real SRM gradient clipped to the style's range.
- **Flavors = word steps:** each flavor row is a segmented control of
  qualitative words — none / hint / present / bold. "None" doubles as the
  avoid state (rosewood fill). Style-mentioned flavors arrive pre-set as
  defaults; "+ add flavor" opens a searchable list (style-relevant first);
  max five flavor rows.
- Generate: single dark-ink serif button. Advanced (OG, attenuation,
  equipment) stays collapsed per issue decisions.

## Rejected in this session

- "Pours at" label on the pour band (kept the band itself).
- Editorial sentence with em-dashes / "leaning" phrasing.
- Ink-bar and chip-row brief headers.
- Mobile swipe deck and vertical card list.
- Binary more/less flavor chips, intensity dots, mini sliders.
