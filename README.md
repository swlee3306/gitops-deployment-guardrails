# GitOps Deployment Guardrails

A dependency-free, read-only checker for rendered Kubernetes JSON. Catch risky
deployment settings before they enter a deployment pipeline, without connecting to a cluster.

Python 3.11+. [한국어 안내](README.ko.md)

```sh
python3 -m guardrails check examples/safe.json
python3 -m guardrails check examples/unsafe.json
python3 -m unittest discover -s tests -v
```

The first command exits `0`. The second intentionally exits `1` and prints rule IDs
and object locations. All example names, image digests and values are synthetic.
The example image does not exist; these fixtures are for static checks, not deployment.

## Example report

```json
{
  "inspected": 1,
  "findings": [
    {"rule": "HOST_ACCESS", "location": "resources[0]"},
    {"rule": "IMAGE_DIGEST", "location": "resources[0].containers[0]"}
  ],
  "uninspected": []
}
```

This excerpt shows the report format; the unsafe fixture produces additional findings.
Policy reports do not echo Secret payloads, environment values or resource names.
Change plans include resource identities (kind, namespace and name), but not manifest values.

## Policy

| Rule | Rejected pattern |
| --- | --- |
| `SECRET_PAYLOAD` | Nonempty Secret `data` or `stringData` |
| `LITERAL_CREDENTIAL` | Credential-like environment/ConfigMap key with a literal value |
| `IMAGE_DIGEST` | Container image without a SHA-256 digest |
| `HOST_ACCESS`, `HOST_PATH` | Host namespace sharing or hostPath volumes |
| `PRIVILEGED`, `PRIVILEGE_ESCALATION` | Privileged execution or missing escalation prevention |
| `ROOT_USER`, `WRITABLE_ROOT` | Root execution or writable root filesystem |
| `SECCOMP`, `CAPABILITIES` | Missing seccomp confinement or capabilities beyond dropping ALL |
| `SERVICE_ACCOUNT_TOKEN` | Service account token automount not explicitly disabled |
| `RESOURCE_BUDGET` | Missing/zero/unsupported CPU or memory requests and limits |
| `RBAC_WILDCARD` | Wildcards in Role/ClusterRole rules |

This is an opinionated baseline, not a policy suitable for every workload. For example,
some legitimate controllers require API access. Treat a finding as a review gate and
adapt policy with tests; do not blindly mutate a live workload.

## Inputs and exit codes

Accepts one resource, an array, or a Kubernetes `List`. Inspectable resources are
Pod, Deployment, StatefulSet, DaemonSet, ReplicaSet, Job, CronJob, Role, ClusterRole,
Secret and ConfigMap. Workload checks include init and ephemeral containers and
inherit relevant Pod security defaults.

Other kinds appear in `uninspected` and cause exit `1`; they are not silently approved.
The checker caps input at 2 MB / 1,000 resources and rejects duplicate JSON keys.

| Exit | Meaning |
| --- | --- |
| 0 | No selected policy violations; no uninspected resource kinds |
| 1 | Policy findings or uninspected resource kinds |
| 2 | Malformed input, unsupported field shapes, or local file errors |

Provide JSON produced by your existing rendering stage. Raw YAML, Helm rendering,
cluster schema validation, admission webhooks and deployment are outside this tool.
Resource quantities use a restricted syntax; the checker does not validate every
Kubernetes quantity representation, version-specific field or workload requirement.

## Integration

Compare two local render artifacts before deployment:

```sh
python3 -m guardrails plan --before examples/safe.json --after examples/safe.json
```

The result distinguishes create/update/delete/unchanged by resource identity. Desired
configuration must pass policy. Deletion is blocked unless `--allow-delete` acknowledges
it in the plan; this flag never deletes anything. Server-managed metadata is ignored.
Manifest values are not included in the plan. This is a local render comparison, not
a cluster drift detector or a replacement for server-side validation.

Run the checker on a local render artifact before the deployment stage and require
exit `0`. This repository does not apply manifests or rewrite your source files.
The supplied `.env.example` is explanatory; no credentials or environment settings
are needed for static checks.

Use `valueFrom.secretKeyRef` for a workload's credential reference. Keep the actual
secret outside the repository. Synthetic negative tests intentionally include fake
literal values so that detection behavior stays reproducible.

## Test strategy

Tests check positive and negative policy paths, nested CronJobs, init containers,
secret references, wildcard RBAC, malformed input, duplicate keys, exit codes and
absence of secret values in reports. CI is configured for Python 3.11–3.13; no hosted
run or production deployment is claimed by the presence of that configuration.

The checker is a static policy tool, not a comprehensive secret or vulnerability
scanner. See [security guidance](SECURITY.md). A distribution license has not yet
been selected.
