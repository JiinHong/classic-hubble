# Composer repertoire browsing

Only show forms represented in the current composer's public catalogue. Single-select
links follow the [Material filter chip](https://m3.material.io/components/chips/guidelines)
pattern. Filter before paginating, keep the selection in the URL and leave the
composer biography and concert search available throughout.

1. Compare the core Chopin genres with the [Chopin Institute](https://chopin.nifc.pl/en/chopin/gatunki/)
   and work/movement identity with the [Köchel catalogue](https://kv.mozarteum.at/en).
2. Import exact-identity Wikidata form and genre claims (P7937 and P136, CC0) with
   `node scripts/generate-work-genres.mjs`. This is an offline reference; new
   works with an explicit form in their title are recognized without a refresh.
3. Group only documented component relationships whose two endpoints are present
   for this composer. Preserve the individual work links. Do not derive program
   matches or change any concert or watchlist relationships.
4. Test form precedence, independently titled works, collection membership,
   multi-page reads, and the public mobile and desktop filter flows.

The additive repertoire repair manifest records the publisher / catalogue and the
exact external identity for Chopin Op. 29 and 36 and Mozart K. 492 and 621.
The individual movements of Chopin Op. 4 and 58 follow the
[Chopin Society's incipit catalogue](https://www.chopin.pl/katalog_part_09.en.html);
the same catalogue identifies the funeral march as movement III of Op. 35.
Both existing entries for that movement remain linkable. These are catalogue
changes, not evidence that an entire work was performed.

For local opera identifiers without a Wikidata genre, compare the exact whole
work against the [Puccini catalogue](https://catalog.puccini.it/works),
[Verdi publisher catalogue](https://www.umpclassicsandscreen.com/en-GB/Composers/V/Verdi-Giuseppe.aspx),
and the respective composer's stage catalogue. Do not propagate an opera's
form to arias or transcriptions by title.
