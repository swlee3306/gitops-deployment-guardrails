"""Compare render artifacts without applying or emitting manifest values."""
import json
import re
from .core import check, InvalidManifest


def index(document):
    resources=document if isinstance(document,list) else document.get('items',[]) if document.get('kind')=='List' else [document]
    result={}
    for item in resources:
        meta=item.get('metadata',{});name=meta.get('name');namespace=meta.get('namespace','default')
        if not all(isinstance(v,str) and re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,252}',v) for v in [name,namespace]):
            raise InvalidManifest('resource identity')
        key=(item['apiVersion'],item['kind'],namespace,name)
        if key in result:raise InvalidManifest('duplicate resource')
        normalized={k:v for k,v in item.items() if k not in {'status','metadata'}}
        normalized['metadata']={k:v for k,v in meta.items() if k not in {'managedFields','resourceVersion','uid','generation','creationTimestamp'}}
        result[key]=json.dumps(normalized,sort_keys=True,separators=(',',':'))
    return result


def plan(before,after,allow_delete=False):
    check(before);policy=check(after)
    old,new=index(before),index(after);actions=[]
    for key in sorted(old.keys()|new.keys()):
        action='create' if key not in old else 'delete' if key not in new else 'update' if old[key]!=new[key] else 'unchanged'
        actions.append({'action':action,'apiVersion':key[0],'kind':key[1],'namespace':key[2],'name':key[3]})
    blocked=bool(policy['findings'] or policy['uninspected'] or (not allow_delete and any(a['action']=='delete' for a in actions)))
    return {'mode':'plan-only','blocked':blocked,'deletion_review_required':not allow_delete and any(a['action']=='delete' for a in actions),'actions':actions,'policy':policy}
