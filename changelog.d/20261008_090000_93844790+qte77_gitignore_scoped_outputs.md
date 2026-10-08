### Security

- `.gitignore`: ignore `scope.*.toml` (except `scope.example.toml`) and
  `inventory/api_endpoints.json` at any depth, so per-target scope files and inventories
  can no longer be committed by accident.
