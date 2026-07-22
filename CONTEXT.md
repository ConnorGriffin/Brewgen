# Brewgen

Brewgen turns beer-style and sensory constraints into fermentable grain bills. The first public release covers fermentables only.

## Language

**Grain bill**:
The fermentable ingredients in a beer and their proportions; it excludes hops and yeast.
_Avoid_: Recipe, complete recipe

**Generated grain bill**:
One grain bill that satisfies the requested style, sensory, color, equipment, and ingredient constraints. When Brewgen returns several, letters identify them without implying order or quality; Brewgen explains their compositional and sensory differences but does not choose an overall winner.
_Avoid_: Recipe alternative, best recipe, recommendation

**Grain-bill set**:
The generated grain bills returned for one brief. Every member satisfies the brief and has a meaningfully distinct complete sensory profile; requested and avoided flavors carry the most weight when Brewgen decides whether two grain bills are too similar. The set has no overall ranking.
_Avoid_: Ranked results, random alternatives

**Reference corpus**:
The deliberately acquired, normalized collection of source recipes used to derive Brewgen's style statistics.
_Avoid_: Reference database, training database

**Style model**:
The reproducible statistics derived from the reference corpus for one beer style.
_Avoid_: Reference data
