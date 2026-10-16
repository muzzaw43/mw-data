# Card database updater

`mtg_cards_slim.json` is the card database the deck tracker app reads (`dbUrl` in the data repo's config).

- **build_slim.py** rebuilds it from MTGJSON AtomicCards (one entry per card, one Commander legality per card).
- **.github/workflows/update-cards.yml** runs it weekly and on demand. It writes `staging/mtg_cards_slim.json` and `staging/SUMMARY.md` and never touches the live file by itself.
- To go live: Actions → *Update card database* → *Run workflow* with **publish** ticked. That copies the staged file over `mtg_cards_slim.json`.
- **watch.txt** lists cards the summary reports on (is it in the new file? in the live file?).
- **test_build_slim.py** turns the live file back into MTGJSON form, rebuilds it and requires an exact match. It also runs in the workflow before each build.

Output format: `{"Card Name": [face, ...]}`, compact JSON, no trailing newline, `commanderLegal` true only when MTGJSON says Legal.
