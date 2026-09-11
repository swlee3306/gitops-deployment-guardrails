import argparse
import json
from pathlib import Path
from .core import check, InvalidManifest


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise InvalidManifest('duplicate JSON key')
        result[key]=value
    return result


def reject_constant(_): raise InvalidManifest('nonfinite JSON number')


def main():
    parser=argparse.ArgumentParser(description='Read-only policy checks for rendered Kubernetes JSON. No cluster access.')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('check');run.add_argument('manifest',type=Path)
    args=parser.parse_args()
    try:
        if args.manifest.stat().st_size>2_000_000: raise InvalidManifest('size limit')
        data=json.loads(args.manifest.read_text(encoding='utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)
        result=check(data)
        print(json.dumps(result,indent=2))
        return 1 if result['findings'] or result['uninspected'] else 0
    except (ValueError, TypeError, OSError, RecursionError):
        print(json.dumps({'status':'invalid_input','message':'Expected bounded Kubernetes JSON objects with supported field shapes.'}))
        return 2


if __name__=='__main__':raise SystemExit(main())
