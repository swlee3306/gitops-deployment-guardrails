# Security and data handling

Keep live credentials and production manifests out of examples, tests and issue
reports. Use synthetic reproductions. The checker returns rule IDs and structural
locations, not resource values.

Static findings are not proof of exploitability, and a passing result is not proof
of security. This policy does not inspect images, dependencies, encoded secrets,
arbitrary application configuration or cluster behavior.

The process reads an input file and emits JSON. It never applies manifests, contacts
a cluster or rotates credentials. Integrations should run on local render artifacts
and retain their own schema validation, approval and secret-management controls.
