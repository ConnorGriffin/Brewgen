# Brewgen

Brewgen turns beer-style and sensory constraints into fermentable grain bills. The first public release covers fermentables only.

## Language

**Grain bill**:
The fermentable ingredients in a beer and their proportions; it excludes hops and yeast.
_Avoid_: Recipe, complete recipe

**Recipe alternative**:
One generated grain bill that satisfies the requested style, sensory, color, equipment, and ingredient constraints. Alternatives are choices, not a quality ranking.
_Avoid_: Best recipe, recommendation

**Reference corpus**:
The deliberately acquired, normalized collection of source recipes used to derive Brewgen's style statistics.
_Avoid_: Reference database, training database

**Style model**:
The reproducible statistics derived from the reference corpus for one beer style.
_Avoid_: Reference data

