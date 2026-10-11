# Third-party notices

This repository's original material is Apache-2.0. It calls dependencies rather
than incorporating their source code. The Python wheel does not bundle Shapely,
GEOS, or NumPy binaries. Package installers resolve those dependencies separately.

| Component | Role | License and provenance |
|---|---|---|
| Shapely | Python planar geometry runtime | BSD-3-Clause; [upstream](https://github.com/shapely/shapely). `third_party/SHAPELY-LICENSE.txt` preserves the notice from Shapely 2.2.0. |
| GEOS | Shapely's native geometry backend | LGPL-2.1; [upstream](https://github.com/libgeos/geos). `third_party/GEOS-LICENSE.txt` preserves the license distributed with Shapely 2.2.0. |
| NumPy | Shapely's runtime dependency | BSD-3-Clause for NumPy's original code; [upstream licenses](https://github.com/numpy/numpy/blob/main/LICENSE.txt). Its distributions may carry additional bundled-library notices. |

The upstream notices still apply when redistributing those components. This
project's Apache license does not relicense them. `uv.lock` records the resolved
development environment; test and build tools are not runtime requirements.

License observations were checked on 2026-10-10. The copied license texts are
not a claim that every future dependency distribution contains the same bundled
libraries; use the notices that accompany the versions you distribute.
