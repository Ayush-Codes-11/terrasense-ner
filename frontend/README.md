# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend enabling type-aware lint rules by installing `oxlint-tsgolint` and editing `.oxlintrc.json`:

```json
{
  "$schema": "./node_modules/oxlint/configuration_schema.json",
  "plugins": ["react", "typescript", "oxc"],
  "options": {
    "typeAware": true
  },
  "rules": {
    "react/rules-of-hooks": "error",
    "react/only-export-components": ["warn", { "allowConstantExport": true }]
  }
}
```

See the [Oxlint rules documentation](https://oxc.rs/docs/guide/usage/linter/rules) for the full list of rules and categories.
# 2D GIS command centre

The dashboard uses Leaflet with the canonical NER boundary APIs. It requests
only the current hierarchy level and switches to the 25-zone prototype grid
after Aizawl is selected. The map uses the standard OpenStreetMap raster tile
endpoint with visible attribution. OSM tiles are community-funded,
best-effort infrastructure with usage limits and no operational SLA; this
prototype does not claim them as a production disaster-operations basemap.
Use a contracted or self-hosted tile service before production deployment.

Risk labels are relative prototype scores. State and boundary-only districts
do not receive fabricated risk values. The committed ADM1 2011 / ADM2 2021
boundaries remain a prototype dataset and are not presented as a definitive
2026 administrative list.
