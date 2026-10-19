"""Check synthetic training names against explicitly supplied local private sources."""
import argparse
import csv
import json
from pathlib import Path

from dataset_split import key, read_rows, validate_synthetic


def private_keys(invoices, catalogs, reviewed):
    names=set()
    for path in invoices:
        with path.open(encoding='utf-8-sig',newline='') as stream:
            reader=csv.DictReader(stream)
            if '消費明細_品名' not in (reader.fieldnames or []):
                raise ValueError('invalid_invoice_header')
            for row in reader:
                name=row.get('消費明細_品名')
                if name and name.strip():names.add(key(name))
    for path in catalogs:
        catalog=json.loads(path.read_text(encoding='utf-8-sig'))
        if not isinstance(catalog,dict):raise ValueError('invalid_catalog')
        names.update(key(name) for name in catalog)
    for path in reviewed:
        for row in read_rows(path):names.add(key(row['name']))
    return names


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--synthetic',type=Path,required=True)
    parser.add_argument('--invoice',action='append',type=Path,default=[])
    parser.add_argument('--catalog',action='append',type=Path,default=[])
    parser.add_argument('--reviewed',action='append',type=Path,default=[])
    parser.add_argument('--public-text',action='append',type=Path,default=[])
    parser.add_argument('--local-match-report',type=Path,help='PRIVATE local JSON for human review; never commit or print its contents')
    args=parser.parse_args()
    if not (args.invoice or args.catalog or args.reviewed):
        parser.error('At least one local private source is required')
    try:
        rows=validate_synthetic(read_rows(args.synthetic))
        private=private_keys(args.invoice,args.catalog,args.reviewed)
        if not private:raise ValueError('empty_private_reference')
        overlaps=sum(key(r['name']) in private for r in rows)
        text_matches=0
        local_details=[]
        for path in args.public_text:
            content=path.read_text(encoding='utf-8-sig')
            public_text=key(content)
            matched=sorted(name for name in private if name in public_text)
            text_matches+=len(matched)
            if args.local_match_report:
                local_details.append(dict(file=str(path.resolve()),matches=[dict(normalized_name=name,
                    line_numbers=[i for i,line in enumerate(content.splitlines(),1) if line.strip() and name in key(line)]) for name in matched]))
        if args.local_match_report:
            with args.local_match_report.open('x',encoding='utf-8') as stream:
                json.dump(local_details,stream,ensure_ascii=False,indent=2)
        print(json.dumps(dict(synthetic_total=len(rows),per_category={str(c):sum(r['category']==c for r in rows) for c in range(10)},
                              private_names_checked=len(private),normalized_exact_matches=overlaps,
                              public_text_files_checked=len(args.public_text),public_text_private_matches=text_matches)))
        return 1 if overlaps or text_matches else 0
    except (ValueError,KeyError,TypeError,OSError):
        parser.exit(1,'Synthetic audit failed; check local source formats.\n')


if __name__=='__main__': raise SystemExit(main())
