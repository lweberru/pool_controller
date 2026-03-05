Release notes templates for `tools/release_hacs.py`

Usage with VS Code tasks:
- `HACS: Release both (notes files)`
- `HACS: Release both major (notes files)`
- `HACS: Prepare both (notes files)`
- `HACS: Prepare both major (notes files)`

Rules:
- One line = one bullet point in GitHub Release notes.
- Empty lines are ignored.
- Leading `- ` or `* ` is optional and stripped.
- Files used by tasks:
  - `release_notes/backend.md`
  - `release_notes/frontend.md`
