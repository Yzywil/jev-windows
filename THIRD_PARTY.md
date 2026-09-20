# Attribution and dependency boundaries

- **Sac-Y/Jev-cu** — architectural inspiration for observe/decide/policy/act/verify.
  https://github.com/Sac-Y/Jev-cu . Its source was not copied. Its package metadata
  lists ISC, but this project does not rely on redistribution permission for that code.
- **CursorTouch/Windows-MCP v0.8.5** — optional runtime dependency, MIT.
  https://github.com/CursorTouch/Windows-MCP/tree/v0.8.5 . We use its packaged
  `windows_mcp.uia` implementation; upstream license files remain in its distribution.
  We do not bundle its source/binaries or relicense its dependencies.
- **TypeSafe** — external commercial API, separate service terms and billing.
  https://docs.typesafe.ai/api . TypeSafe and Jev names identify integration support,
  not affiliation or endorsement.
- **Cua jev-use example** — research reference for immutable candidates and independent
  verification. https://github.com/trycua/cua/tree/main/libs/cua-driver/examples/jev-use .
  No Cua source or proprietary host runtime is bundled.

`uv.lock` records the exact development resolution, hashes, sources and Windows
optional dependency graph. The MIT license applies to this project's original
source, not third-party packages or hosted services.

