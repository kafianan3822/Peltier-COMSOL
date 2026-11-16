Optional: save the COMSOL library material *Ge - Germanium* here as `Ge_library.mph`
(1D model, component `comp1`, material tag `mat1`). The builders copy all of its
property groups; without it they use the explicit germanium table `material_fallback` of
`config/params_base.yaml` (the recommended setup: the reference model uses the same numbers).
See docs/GUI_build_steps.md, stage 2, and CHANGES.md M4-M5.
