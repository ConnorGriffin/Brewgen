# Brewgen - Homebrew Recipe Generator

A web application for generating beer recipes based on desired flavor characteristics rather than selecting ingredients manually.

## Overview
This is still a major work-in-progress and was built as a way for me to learn Flask, Node, Vue, and how to put it all together into a web application.

Brewgen uses per-style aggregate models combined with the BJCP 2015 guidelines to generate grain bills. For fermentables, the models capture average fermentable type (Pale 2-Row, Maris Otter, Vienna, etc.) and category (Base, Munich, Caramel, Roasted, etc.) usage, combined with maltsters' sensory descriptors to build a flavor profile per style. For example, the American IPA model shows a Bready range of 0–2.13 out of 5, mean 0.66. Requesting an American IPA with Bready '>2.0' yields grain bills that lean on Golden Promise and Munich malts.

**Style model provenance:** The current style models are legacy derived artifacts produced from a corpus scraped from BeerSmith Recipes and Brewers Friend. The raw corpus is not in this repository and cannot be recovered; the models are not currently reproducible or rights-cleared. See [`recipe_analyzer/PROVENANCE.md`](recipe_analyzer/PROVENANCE.md) for full disclosure.


## Example
Generating an American Pale Ale recipe that's high Malty/Honey, and very low Toast flavor.
![American Pale Ale Demo](docs/images/pale-ale-demo.gif)

## Project Status

The goal of this project is to eventually add in Hop and Yeast modules, streamline the recipe design process, publish the app online, add a way to save/share recipes, and also export them to beerxml or other supported formats. 

The grain bill generation is functional but very clunky. You have to essentially add in your restrictions iteratively, and it's very granular. If you aren't very specific with your requirements it will generate hundreds of similar recipes. I hope to instead implement some kind of rating system for each descriptor, where a user can pick up to say 5 descriptors, and can specify if they should be above/below style average by some amount, then only a few recipes will be presented to the user. 

