# LCP PO Key Generator

Standalone Python 3 utility for mapping legal entities to existing LCP keys and creating new SFGL PO keys for unmatched names. No third-party dependencies.

## Input files

- `master.csv`: columns `SS_CODE`, `LCP_KEY`, `LCP_NAME`.
- `source.csv`: column `WP_ENTITY__C` (configurable). Multiple legal entities in one cell are separated by `;`.

## Run

```bash
python lcp_po_generator.py --master master.csv --source source.csv --source-column WP_ENTITY__C --prefix PO1101 --suffix-length 6
```

Optional: `--output-dir lcp_output` and `--delimiter ';'`.

## Matching and generation

- Compare names after trimming surrounding whitespace and converting to uppercase.
- Reuse existing master keys, preferring `SFGL`, then `NAP`, then other sources; break ties by LCP key.
- For unmatched normalized names, take the maximum numeric suffix of master keys with the configured prefix and assign consecutive suffixes in normalized alphabetical name order.
- Newly generated records use `SS_CODE=SFGL`.
- Source file and master are never overwritten.

## Outputs

- `LCP_Mapping.csv`: one row per source legal entity with status `EXISTING` or `NEW`.
- `New_LCP_Records.csv`: generated SFGL records only.
- `Updated_LCP_Master.csv`: original master plus generated records.

## Important

The script computes new IDs using MAX + row number, not a database sequence. Always use the latest authoritative master and review the generated records before importing. Concurrent runs against the same master can create colliding keys. Keep production master and source data out of this repository.
