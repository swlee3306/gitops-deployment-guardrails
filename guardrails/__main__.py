import argparse
import json
from pathlib import Path
from .core import check, InvalidManifest
from .plan import plan


def unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise InvalidManifest('duplicate JSON key')
        result[key]=value
    return result


def reject_constant(_): raise InvalidManifest('nonfinite JSON number')


def load(path):
    if path.stat().st_size>2_000_000:raise InvalidManifest('size limit')
    return json.loads(path.read_text(encoding='utf-8'),object_pairs_hook=unique_object,parse_constant=reject_constant)


def main():
    parser=argparse.ArgumentParser(description='Read-only policy checks for rendered Kubernetes JSON. No cluster access.')
    sub=parser.add_subparsers(dest='command',required=True)
    run=sub.add_parser('check');run.add_argument('manifest',type=Path)
    preview=sub.add_parser('plan',help='compare local render artifacts; never apply')
    preview.add_argument('--before',type=Path,required=True)
    preview.add_argument('--after',type=Path,required=True)
    preview.add_argument('--allow-delete',action='store_true',help='acknowledge deletion in the plan only')
    args=parser.parse_args()
    try:
        if args.command=='plan':
            result=plan(load(args.before),load(args.after),args.allow_delete)
            print(json.dumps(result,indent=2))
            return 1 if result['blocked'] else 0
        result=check(load(args.manifest))
        print(json.dumps(result,indent=2))
        return 1 if result['findings'] or result['uninspected'] else 0
    except (ValueError, TypeError, OSError, RecursionError):
        print(json.dumps({'status':'invalid_input','message':'Expected bounded Kubernetes JSON objects with supported field shapes.'}))
        return 2


if __name__=='__main__':raise SystemExit(main())
