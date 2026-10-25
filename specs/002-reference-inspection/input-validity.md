# Input applicability and evidence correction

## Defect

Unrelated images could receive a fixed central fuselage box. Fin fallback logic
converted left/right edge-count asymmetry into an angle, without detecting fins.
The body module also claimed zero missing components without an inventory check.
These were unsupported inferences, not measurements of the uploaded object.

## Correction

- `cv/subject.py` conservatively checks image quality and corroborating geometry:
  paired upright body walls, converging nose edges, and two attached fin edges.
  It derives coordinates from pixels, not image-center coordinates or filenames.
  Ambiguous or unsupported views abstain rather than selecting a default box.
- Body and fin modules return degraded warnings with no overlays or angle metrics
  when applicability is unverified. The original screenshot and synthetic notebooks
  are covered by regression tests. Renaming a notebook `rocket.jpg` does not help.
- Fin deviation uses the difference between two measured projected leading-edge
  inclinations. Edge counts are never relabeled as degrees. This is not calibrated
  3D fin alignment, aerodynamic stability, or a physical crack-width measurement.
- The unconditional missing-parts result is replaced by `body.visible_geometry`,
  describing only the coarse components observed. Individual fittings and inventory
  completeness are explicitly not assessed.
- Body surface findings describe sampled pixel texture, edges and darkness, not
  definitive cracks, dents, burns or absence of all damage. Seams, markings and
  shadows can produce the same signals. Use reference comparison and manual review.
- Single-image and graph/quadrant upload paths skip pad/cue assessment on unsupported
  subjects. The separate launchpad-monitor workflow is not restricted to rocket views.
- Baseline enrollment rejects unsupported reference images. Legacy baselines are
  rechecked before quadrant reference analysis. Reference alignment may still compare
  damaged current images against an applicable baseline even when damage obscures fins.
- The CV fail-safe wrapper also handles empty results and applies the confidence
  floor to results; it does not raise confidence to manufacture an OK result.
- The inspect view permanently explains applicability and limitations. All verdicts
  remain exclusively computed by the unchanged deterministic rule engine.

The synthetic fin fixture was regenerated with asymmetric leading edges for the
corrected angle measurement. Verdicts and measurements are still computed from its
pixels, not its filename or scenario label. No fixture lookup is used for uploads.

## Remaining limits

This is a conservative geometric applicability filter, not a trained semantic rocket
classifier. It supports clear upright side views, not every rocket shape, perspective,
occlusion, lighting condition or camera resolution. Rocket-like non-rocket objects can
still be ambiguous; no general recognition or field-accuracy guarantee is made.
The bundled COCO detector is not a trained rocket/crack detector. Reliable field use
requires representative labeled rocket/defect data, trained models and independent
validation. A dark patch is not evidence of a confirmed burn; a low texture score is
not evidence that every surface is dent-free. Surface sampling is partial.
Heuristic confidence values are not calibrated probabilities of object identity or
defect detection accuracy. The applicability filter must not be used as certification.

Existing saved reports are historical records and are not silently rewritten. Start
a new run after restarting the backend to use the corrected implementation.

## Verification

- 130 backend tests passed, including the original local screenshot, generated
  documents, noise, blank/landscape/rectangle inputs, shifted/resized/grayscale
  rocket fixtures, both upload modes, and confidence/empty-result fail-safes.
- Strict mypy (48 source files) and Ruff passed.
- All 57 frontend tests, TypeScript and ESLint passed.
- Production build and the 11-scenario browser suite passed. The notebook flow
  asserts HOLD, Not evaluated status, no rocket overlays, no fin-angle finding,
  and the visible disclaimer. The notebook region cropped from the supplied local
  screenshot was also checked directly and returned degraded body/fin warnings
  without overlays.
- The original monitor latency budget remains unchanged. A run during concurrent
  builds exceeded it; the full serial backend run passed the same timing check.

Checks used the existing Python 3.12.8 environment, not an independently validated
Python 3.11 installation. These tests are not representative field-accuracy validation.

Decision-support tool. Not a replacement for certified range safety.
