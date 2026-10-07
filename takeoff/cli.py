import argparse
import json
from pathlib import Path
from .engine import calculate, compare_baseline, export, extract
from .sample import create_sample


def main():
    parser = argparse.ArgumentParser(description='검토를 거친 급수 DXF 평면 길이 산출')
    sub = parser.add_subparsers(dest='command', required=True)
    sample = sub.add_parser('sample'); sample.add_argument('directory')
    inspect = sub.add_parser('inspect'); inspect.add_argument('source'); inspect.add_argument('output')
    run = sub.add_parser('run')
    run.add_argument('source'); run.add_argument('decisions'); run.add_argument('output')
    run.add_argument('--unit', required=True, choices=['mm', 'cm', 'm'])
    run.add_argument('--unit-evidence', required=True)
    run.add_argument('--rules', default=str(Path(__file__).resolve().parents[1] / 'rules/planar-v1.json'))
    run.add_argument('--baseline')
    args = parser.parse_args()
    if args.command == 'sample':
        print(create_sample(args.directory)); return
    extraction = extract(args.source)
    if args.command == 'inspect':
        with open(args.output, 'x', encoding='utf-8') as f:
            json.dump(extraction, f, ensure_ascii=False, indent=2)
        return
    decisions = json.loads(Path(args.decisions).read_text())
    rules = json.loads(Path(args.rules).read_text())
    result = calculate(extraction, decisions, args.unit, args.unit_evidence, rules)
    if args.baseline:
        result['comparison'] = compare_baseline(result, args.baseline)
    export(args.source, args.output, extraction, result)
    print(json.dumps({'summary': result['summary'], 'counts': result['counts'], 'output': args.output}, ensure_ascii=False))


if __name__ == '__main__':
    main()
