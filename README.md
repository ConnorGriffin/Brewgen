# Brewgen - Homebrew Recipe Generator

A web application for generating beer recipes based on desired flavor characteristics rather than selecting ingredients manually.

## Overview
This is still a major work-in-progress and was built as a way for me to learn Flask, Node, Vue, and how to put it all together into a web application. 

I analyzed a large number of public recipes, combined that data with the BJCP 2015 guidelines, and built a model for each style. For fermentables, I analyzed the average fermentable type (Pale 2-Row, Maris Otter, Vienna, etc.) and fermentablue category (Base, Munich, Caramel, Roasted, etc.) usage across recipes, and then used the maltsters' sensory descriptors for their grains to build a possible flavor profile. For example, according to my analysis, the typical American IPA has a range of 0-2.13 out of 5 for "Bready", with a mean of 0.66. You can ask Brewgen for an American IPA recipe with Bready '>2.0', yielding recipes that use high percentages of Golden Promise and Munich malts, which both are high in "Bready" character according to the malster's sensory data.


## Example
Generating an American Pale Ale recipe that's high Malty/Honey, and very low Toast flavor.
![American Pale Ale Demo](docs\images\pale-ale-demo.gif)

## Project Status

The goal of this project is to eventually add in Hop and Yeast modules, streamline the recipe design process, publish the app online, add a way to save/share recipes, and also export them to beerxml or other supported formats. 

The grain bill generation is functional but very clunky. You have to essentially add in your restrictions iteratively, and it's very granular. If you aren't very specific with your requirements it will generate hundreds of similar recipes. I hope to instead implement some kind of rating system for each descriptor, where a user can pick up to say 5 descriptors, and can specify if they should be above/below style average by some amount, then only a few recipes will be presented to the user. 

