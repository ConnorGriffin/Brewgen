# Reference-corpus source research

Date: 2026-07-21

Question: can Brewgen obtain a useful corpus of public beer recipes without
crawling recipe sites, and who could authorize one?

## Bottom line

Issue #27 assumed an acquisition channel that is not currently evidenced. The
major services let a user bulk-export **their own** recipes and let visitors
download public recipes individually. None documents a site-wide public dump or
site-wide API. A no-scraping corpus is therefore possible only by:

1. negotiating a data license and export with a platform operator;
2. collecting exports directly from recipe authors under an explicit reuse
   license; or
3. starting with a small, deliberately published collection such as BrewDog's
   DIY Dog recipes.

There is no discovered drop-in, large, openly licensed corpus with the
fermentable ingredients Brewgen needs. The 75,000-row Kaggle dataset is not that:
it was scraped from Brewer's Friend, its uploader—not Brewer's Friend or the
recipe authors—marked it CC0, and its published columns omit ingredient bills.

## What each service actually exports

| Source | First-party evidence | What it establishes | Site-wide corpus? |
|---|---|---|---|
| Brewer's Friend | [Bulk export announcement](https://www.brewersfriend.com/2015/04/08/new-recipe-bulk-export-backup-ability/) says “export all of **your** recipes”; [API docs](https://docs.brewersfriend.com/api/recipes) say “Search All **My** Recipes” | Account backup and account-scoped API, plus one-recipe BeerXML retrieval | No documented dump or public-corpus API |
| BeerSmith | [FAQ](https://beersmith.com/faq/) documents BSMX export and says users can mark individual cloud recipes public; [cloud documentation](https://beersmith.com/blog/2019/01/06/beersmith-cloud-recipe-privacy-and-sharing-explained/) says shared recipes can be found and downloaded | Local/account export and individual public sharing | No documented dump or public API |
| Brewfather | [API docs](https://docs.brewfather.app/api) say the recipes endpoint lists “your recipes”; [library docs](https://docs.brewfather.app/library) offer browse, copy, and progressive loading of public recipes | Account-scoped API and interactive public library | No documented dump or public-library API |
| BrewToad | The service is defunct. Contemporary shutdown discussion described individual BeerXML URLs; no first-party bulk archive was found | Historical one-recipe export only | No surviving authorized dump found |

BeerXML is an exchange **format**, not a recipe database. Its specification says
its purpose is exchanging recipes and other brewing data; it supplies a schema,
not a corpus ([BeerXML specification](https://www.beerxml.com/beerxml.htm)). The
same distinction applies to BeerJSON and DotBeer.

## Available datasets

### Potentially usable, but small or constrained

- **BrewDog DIY Dog.** BrewDog's first-party 2017 release contains 262
  “homebrew-ready” recipes and expressly encourages readers to recreate, modify,
  and experiment with them ([BrewDog announcement](https://efp.brewdog.com/es/blog/diy-dog-2017)).
  This is the clearest deliberately published recipe collection found. It is
  nevertheless one brewery's back catalogue, not a representative homebrew
  corpus, and the announcement is not a conventional machine-data license.
  Obtain written confirmation before redistributing normalized records or using
  a third-party conversion whose license adds restrictions.

- **Brewtarget samples.** Brewtarget is open-source software and contains sample
  recipes, but its useful “large database” is primarily an ingredient database
  ([Brewtarget features](https://www.brewtarget.org/features.html)). Its small
  bundled recipe set is useful for parser fixtures, not statistical style models.
  The software license does not automatically establish provenance and reuse
  rights for every bundled data record.

### Not clean substitutes

- **Kaggle “Brewer's Friend Beer Recipes.”** The dataset card says it contains
  about 75,000 user-submitted recipes scraped from Brewer's Friend and labels the
  upload CC0 ([dataset card](https://www.kaggle.com/datasets/jtrofe/beer-recipes)).
  Its documented fields cover beer statistics and process settings, not the
  fermentable ingredient names and quantities Brewgen requires. More
  importantly, a downstream uploader can license only rights they hold; the CC0
  label is not evidence that Brewer's Friend or thousands of authors authorized
  corpus reuse.

- **Open Beer / Open Brewery DB.** These are genuinely open databases, but they
  catalogue beers, breweries, and locations rather than brewing recipes
  ([Open Beer](https://openbeer.github.io/), [Open Brewery DB](https://www.openbrewerydb.org/)).

- **PunkAPI mirrors/conversions.** They normalize BrewDog recipes and may be
  technically convenient, but a converter's code license is not necessarily a
  license to the source recipe data. Use the first-party DIY Dog source and clear
  data rights separately.

- **Academic mined corpora.** Recent work reports analysis of 62,121 recipes
  ([Bonatto 2025](https://arxiv.org/abs/2505.17039)), but the paper abstract is
  evidence that a corpus was analyzed, not that it is published or sublicensable.
  The author is a possible introduction to the underlying source owner, not a
  substitute rights grant.

## Who could actually provide an export

The most credible counterparties are the operators that hold the database and
have direct relationships with contributors:

1. **Brewer's Friend.** Ask through its [support form](https://www.brewersfriend.com/feedback-welcome/)
   for a one-time export of public, all-grain recipes plus a written license to
   derive and publish aggregate style models. Its terms must be checked in the
   negotiation; possession of user content does not by itself prove the operator
   can sublicense every use ([terms](https://www.brewersfriend.com/terms/)).

2. **BeerSmith / Brad Smith.** Use BeerSmith's [support/contact route](https://beersmith.com/support/).
   The operator controls the Recipe Cloud and is the only realistic source of a
   clean server-side export. Request public recipes only, minimal fields, stable
   source IDs, and permission for derived statistics—not a republication right
   broader than Brewgen needs.

3. **Brewfather.** Ask the operator for a licensed snapshot of recipes whose
   authors opted into its public library. Its documented API cannot perform this
   job because it is account-scoped ([API](https://docs.brewfather.app/api)).

4. **BrewDog.** Ask BrewDog to confirm machine-readable reuse and derived-model
   publication rights for DIY Dog. This is a much smaller corpus, but the ask is
   simpler because BrewDog authored and deliberately published the recipes.

5. **Recipe authors, clubs, and competitions.** Authors can export their own
   recipes from all three active platforms. Brewgen could accept voluntary
   BeerXML/BeerJSON donations under a clear CC0 or CC BY grant. This is slower and
   selection-biased, but it is the only scalable path that does not depend on a
   platform deal or crawling. Clubs can contribute coherent batches, but each
   contributor must have authority to license the submitted recipes.

The request to a platform should be narrow: public all-grain recipes; recipe ID,
style, gravity/color fields, fermentable names and amounts; no profiles, email,
free-text notes, or other personal data; one static encrypted transfer; right to
normalize, deduplicate, retain provenance, and publish aggregate style models;
and a deletion/rebuild mechanism if a source is revoked.

## What the IP concern really is

This is not legal advice.

- In the United States, a mere list of recipe ingredients is not copyrightable.
  The Copyright Office distinguishes ingredient lists from sufficiently creative
  explanatory text, photographs, and illustrations ([Compendium §313.4(F)](https://www.copyright.gov/comp3/docs/compendium.pdf)).
  Numeric facts such as gravity, color, quantities, and temperatures are likewise
  generally facts, not authored expression. Notes and prose instructions may be
  protected, so Brewgen should not acquire them.

- A collection can still have “thin” copyright in original selection or
  arrangement even when its facts are unprotected. Copying the entire organized
  corpus raises a different question from using isolated recipe facts. A platform
  agreement can also restrict automated access regardless of whether every field
  is copyrightable.

- Public accessibility does not automatically authorize high-volume automated
  retrieval. The Ninth Circuit's *hiQ v. LinkedIn* decision limits one Computer
  Fraud and Abuse Act theory for public pages, but the opinion did not erase
  contract, copyright, trespass, privacy, or other claims
  ([2022 opinion](https://cdn.ca9.uscourts.gov/datastore/opinions/2022/04/18/17-16783.pdf)).

- The EU has a separate database right. Directive 96/9/EC can prohibit extraction
  or reutilization of a substantial part of a database, and repeated systematic
  extraction of insubstantial parts, even when individual facts are not protected
  by copyright ([EUR-Lex, Articles 7–8](https://eur-lex.europa.eu/legal-content/EN/ALL/?uri=CELEX%3A31996L0009)).

The practical conclusion is not “recipes are proprietary.” It is: take only the
functional facts Brewgen needs, omit expressive text and personal data, and get
authorization for the collection-level acquisition.

## Why AI assistants sound protective

The inconsistency is real. AI companies have built products using enormous web
corpora, often without negotiating an individual license for every source, while
their assistants caution users about automated collection. Calling all of that
“stolen” is a disputed legal conclusion; calling much of it scraped and
unlicensed is fair. The companies have argued that training uses are fair use,
and those arguments remain contested rather than universally settled.

The assistant's caution is therefore not a coherent moral verdict that scraping
is always wrong. It combines:

- uncertainty about the user's authorization and the target's terms;
- operational risks such as bypassing access controls or causing load;
- unresolved copyright, contract, privacy, and database-right questions;
- product policies designed to avoid facilitating a risky act; and
- a basic asymmetry: a large company can fund litigation and make a calculated
  fair-use bet, while an assistant cannot accept that risk on a user's behalf.

That is corporate risk control, and sometimes hypocrisy, not proof that Brewgen's
old scraping was criminal or that repeating it is prudent. The technically and
ethically clean line here is authorization at acquisition—not pretending public
pages are secret, and not pretending an unofficial dataset's license badge cures
its provenance.

## Decision for Brewgen

Revise #27's premise: **no verified bulk export currently exists**. Do not start
the corpus pipeline on the assumption that one will appear. First run two bounded
acquisition tracks:

1. request a licensed, minimal public-recipe snapshot from Brewer's Friend,
   BeerSmith, and Brewfather; and
2. request clear reuse permission for DIY Dog while designing a consented recipe
   donation format.

Build the importer against synthetic fixtures and any cleared small source. Do
not ingest the Kaggle scrape or resume site crawling as a shortcut. If no
platform agrees, Brewgen must either launch with a smaller consented corpus or
keep the current derived style models as legacy, provenance-limited artifacts;
it cannot honestly claim that #27 identified a replacement source.
