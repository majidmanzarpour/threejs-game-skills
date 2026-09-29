# Third-party data

`references/animations.csv` lists the `action_id`, name, category, and subcategory of the
animations in Meshy's public animation library, transcribed from the Meshy API
documentation (https://docs.meshy.ai/en/api/animation-library) so the tooling can resolve
clip names offline. It contains identifiers and factual metadata only — no animation data
and no preview media. Meshy is a trademark of its owners; this project is not affiliated
with or endorsed by Meshy.

Regenerate the table when Meshy adds animations:

```bash
curl -sL https://docs.meshy.ai/en/api/animation-library -o library.html
python3 scripts/scrape_animation_library.py library.html references/animations.csv
```
