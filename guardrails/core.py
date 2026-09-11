"""Opinionated, bounded static policy checks; not a Kubernetes schema validator."""
import re


class InvalidManifest(ValueError): pass


def mapping(value):
    if not isinstance(value, dict): raise InvalidManifest('expected object')
    return value


def sequence(value):
    if not isinstance(value, list): raise InvalidManifest('expected list')
    return value


def check(document):
    if isinstance(document, list):
        resources = document
    else:
        document = mapping(document)
        resources = sequence(document.get('items')) if document.get('kind') == 'List' else [document]
    if not resources or len(resources) > 1000: raise InvalidManifest('resource count')
    findings, uninspected = [], []
    def flag(rule, location):
        findings.append({'rule': rule, 'location': location})
    for index, resource in enumerate(resources):
        resource = mapping(resource); kind = resource.get('kind')
        if not isinstance(kind, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9]{0,63}', kind): raise InvalidManifest('invalid kind')
        api = resource.get('apiVersion')
        if not isinstance(api, str) or not api: raise InvalidManifest('missing API version')
        mapping(resource.get('metadata'))
        location = f'resources[{index}]'
        if kind == 'Secret':
            if resource.get('data') or resource.get('stringData'): flag('SECRET_PAYLOAD', location)
            continue
        if kind in {'Role', 'ClusterRole'}:
            for rule in sequence(resource.get('rules', [])):
                rule=mapping(rule)
                for field in ('verbs', 'resources', 'apiGroups', 'nonResourceURLs'):
                    values=sequence(rule.get(field, []))
                    if any(not isinstance(v, str) for v in values): raise InvalidManifest('RBAC value')
                    if any('*' in v for v in values): flag('RBAC_WILDCARD', location + '.rules'); break
            continue
        if kind == 'ConfigMap':
            for key, value in mapping(resource.get('data', {})).items():
                if not isinstance(key, str) or not isinstance(value, str): raise InvalidManifest('ConfigMap data')
                if re.search(r'password|passwd|token|secret|api.?key', key, re.I) and value: flag('LITERAL_CREDENTIAL', location + '.data')
            continue
        if kind == 'Pod':
            pod = mapping(resource.get('spec'))
        elif kind in {'Deployment', 'StatefulSet', 'DaemonSet', 'ReplicaSet', 'Job'}:
            pod = mapping(mapping(mapping(resource.get('spec')).get('template')).get('spec'))
        elif kind == 'CronJob':
            spec = mapping(mapping(mapping(resource.get('spec')).get('jobTemplate')).get('spec'))
            pod = mapping(mapping(spec.get('template')).get('spec'))
        else:
            uninspected.append(kind)
            continue
        if any(pod.get(field) is not False and field in pod for field in ('hostNetwork', 'hostPID', 'hostIPC')):
            flag('HOST_ACCESS', location)
        for volume in sequence(pod.get('volumes', [])):
            if 'hostPath' in mapping(volume): flag('HOST_PATH', location + '.volumes')
        if pod.get('automountServiceAccountToken') is not False: flag('SERVICE_ACCOUNT_TOKEN', location)
        pod_security = mapping(pod.get('securityContext', {}))
        for group in ('containers', 'initContainers', 'ephemeralContainers'):
            containers = sequence(pod.get(group, []))
            if group == 'containers' and not containers: raise InvalidManifest('empty containers')
            for ci, container in enumerate(containers):
                container = mapping(container); loc = f'{location}.{group}[{ci}]'
                image = container.get('image')
                if not isinstance(image, str): raise InvalidManifest('image required')
                if not re.fullmatch(r'[^\s@]+@sha256:[0-9a-f]{64}', image): flag('IMAGE_DIGEST', loc)
                security = mapping(container.get('securityContext', {}))
                if security.get('privileged', False) is not False: flag('PRIVILEGED', loc)
                if security.get('allowPrivilegeEscalation') is not False: flag('PRIVILEGE_ESCALATION', loc)
                if security.get('readOnlyRootFilesystem') is not True: flag('WRITABLE_ROOT', loc)
                if security.get('runAsNonRoot', pod_security.get('runAsNonRoot')) is not True or security.get('runAsUser', pod_security.get('runAsUser')) == 0:
                    flag('ROOT_USER', loc)
                seccomp = mapping(security.get('seccompProfile', pod_security.get('seccompProfile', {})))
                if seccomp.get('type') not in {'RuntimeDefault', 'Localhost'}: flag('SECCOMP', loc)
                caps = mapping(security.get('capabilities', {}))
                if 'ALL' not in sequence(caps.get('drop', [])) or sequence(caps.get('add', [])): flag('CAPABILITIES', loc)
                budget = mapping(container.get('resources', {}))
                for field in ('requests', 'limits'):
                    values = mapping(budget.get(field, {}))
                    if not all(isinstance(values.get(r), (str, int, float)) and not isinstance(values.get(r), bool)
                               and re.fullmatch(r'(?:\d+(?:\.\d+)?|\.\d+)(?:[numkKMGTPE]i?)?', str(values[r]))
                               and float(re.match(r'[\d.]+', str(values[r]))[0]) > 0 for r in ('cpu', 'memory')):
                        flag('RESOURCE_BUDGET', loc + '.' + field)
                for env in sequence(container.get('env', [])):
                    env=mapping(env); name=env.get('name')
                    if not isinstance(name, str): raise InvalidManifest('environment name')
                    if re.search(r'password|passwd|token|secret|api.?key', name, re.I) and 'value' in env:
                        flag('LITERAL_CREDENTIAL', loc + '.env')
    unique = list({(f['rule'], f['location']): f for f in findings}.values())
    return {'inspected': len(resources) - len(uninspected), 'findings': unique, 'uninspected': sorted(set(uninspected))}
