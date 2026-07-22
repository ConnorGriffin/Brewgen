# Style Model Provenance

## Status: Legacy, Unverifiable Provenance

The per-style JSON models in `recipe_analyzer/style_data/` are **legacy derived artifacts**. They were produced from a corpus of homebrew recipes scraped from two public recipe-sharing services — BeerSmith Recipes (beersmithrecipes.com) and Brewers Friend (brewersfriend.com) — and combined with the BJCP 2015 style guidelines.

## What is missing

The raw scraped corpus is not in this repository and has not been recovered. Without it, the models cannot be regenerated, audited, or corrected.

## Rights status

The acquisition and publication rights for both the original recipe corpus and these derived models have not been cleared with either BeerSmith Recipes or Brewers Friend. These models must not be described as openly licensed or rights-cleared.

## What was removed

The live crawler implementations (`beersmith_scrape/scrape.py` and `brewersfriend_scrape/scrape.py`) have been removed from the active codebase. They are preserved in git history but cannot be invoked by any documented or automated workflow. The raw scraped recipes were never committed to this repository and are not distributed with it.

## Current use

The application may continue using these aggregate style models to generate grain bills via the free public grain-bill generator. No claim is made that they are reproducible or rights-cleared.

## Future regeneration

Any future rebuild of these models must use a deliberately acquired, provenance-recorded reference corpus — not a replacement for the retired live crawlers. See issue #27 for the reference-corpus contract that governs future acquisition.
