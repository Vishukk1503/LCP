#!/usr/bin/env python3
"""LCP PO generator matching the Snowflake name-match and MAX+ROW_NUMBER logic.

Inputs are CSV files (Excel: Save As -> CSV UTF-8).
Example:
 python lcp_po_generator.py --master master.csv --source source.csv --source-column WP_ENTITY__C --prefix PO1101 --suffix-length 6
"""
import argparse
import csv
import re
from pathlib import Path


def norm(value):
    return str(value or '').strip().upper()


def load_csv(path):
    with open(path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f'{path}: CSV has no header')
        return list(reader), reader.fieldnames


def write_csv(path, rows, fields):
    with open(path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def require(fields, columns, label):
    missing = [c for c in columns if c not in fields]
    if missing:
        raise ValueError(f'{label}: missing columns {missing}; found {fields}')


def main():
    p = argparse.ArgumentParser(description='Map existing LCP keys and create SFGL PO keys for missing names')
    p.add_argument('--master', required=True, help='Master CSV with SS_CODE, LCP_KEY, LCP_NAME')
    p.add_argument('--source', required=True, help='Source CSV with legal entity column')
    p.add_argument('--source-column', default='WP_ENTITY__C')
    p.add_argument('--delimiter', default=';', help='Separator between multiple legal entities (default ;)')
    p.add_argument('--prefix', required=True, help='PO key prefix, e.g. PO1101')
    p.add_argument('--suffix-length', type=int, required=True, help='Zero-padded numeric suffix width')
    p.add_argument('--output-dir', default='lcp_output')
    args = p.parse_args()
    if args.suffix_length <= 0 or not args.prefix:
        p.error('prefix must be nonempty and suffix-length must be positive')

    master, master_fields = load_csv(args.master)
    source, source_fields = load_csv(args.source)
    require(master_fields, ['SS_CODE', 'LCP_KEY', 'LCP_NAME'], 'master')
    require(source_fields, [args.source_column], 'source')

    index = {}
    for row in master:
        name = norm(row['LCP_NAME'])
        if not name or not str(row['LCP_KEY'] or '').strip():
            continue
        index.setdefault(name, []).append(row)

    def rank(row):
        system = norm(row['SS_CODE'])
        return (0 if system == 'SFGL' else 1 if system == 'NAP' else 2,
                str(row['LCP_KEY'] or ''))

    highest = 0
    for row in master:
        key = str(row['LCP_KEY'] or '').strip()
        if key.upper().startswith(args.prefix.upper()):
            suffix = key[len(args.prefix):]
            if re.fullmatch(r'\d+', suffix):
                highest = max(highest, int(suffix))

    extracted = []
    new_names = {}
    for row_number, row in enumerate(source, start=2):
        for part in str(row.get(args.source_column) or '').split(args.delimiter):
            name = part.strip()
            normalized = norm(name)
            if not normalized:
                continue
            extracted.append((row_number, name, normalized))
            if normalized not in index and normalized not in new_names:
                new_names[normalized] = name

    sorted_new = sorted(new_names.items(), key=lambda item: (item[0], item[1]))
    if highest + len(sorted_new) > 10 ** args.suffix_length - 1:
        raise ValueError('Generated key suffix would exceed the configured width')
    generated = {}
    for rn, (normalized, name) in enumerate(sorted_new, start=1):
        key = f'{args.prefix}{highest + rn:0{args.suffix_length}d}'
        generated[normalized] = {'SS_CODE': 'SFGL', 'LCP_KEY': key, 'LCP_NAME': name}

    mappings = []
    for source_row, name, normalized in extracted:
        if normalized in index:
            chosen = min(index[normalized], key=rank)
            status = 'EXISTING'
        else:
            chosen = generated[normalized]
            status = 'NEW'
        mappings.append({'SOURCE_ROW': source_row, 'SOURCE_LEGAL_ENTITY': name,
                         'SS_CODE': chosen['SS_CODE'], 'LCP_KEY': chosen['LCP_KEY'],
                         'LCP_NAME': chosen['LCP_NAME'], 'STATUS': status})

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / 'LCP_Mapping.csv', mappings,
              ['SOURCE_ROW', 'SOURCE_LEGAL_ENTITY', 'SS_CODE', 'LCP_KEY', 'LCP_NAME', 'STATUS'])
    new_rows = list(generated.values())
    write_csv(out / 'New_LCP_Records.csv', new_rows, ['SS_CODE', 'LCP_KEY', 'LCP_NAME'])
    write_csv(out / 'Updated_LCP_Master.csv', master + new_rows, master_fields)
    print(f'Existing master rows: {len(master)}')
    print(f'Legal entity occurrences mapped: {len(mappings)}')
    print(f'New unique legal entities: {len(new_rows)}')
    print(f'Highest prior numeric suffix: {highest}')
    print(f'Files written to: {out.resolve()}')


if __name__ == '__main__':
    main()
