# D.E.C.R.E.E — LLM Integration Context

## What this service does
Accepts a vehicle damage photo, analyzes it with Claude Haiku 4.5 via AWS Bedrock, and returns a structured damage assessment with cost estimates.

## Endpoint
`POST http://localhost:3000/api/v1/assess` — no auth, open CORS.

## Input
Multipart form with three fields:
- `file` — the image (required)
- `message` — optional text context about the damage
- `mode` — `short` (3-5 sentence summary) or `full` (detailed markdown report, default)

## Output
JSON with a `data` object containing:
- `reportContent` — markdown string, length depends on mode
- `costEstimateLow`, `costEstimateHigh`, `costEstimateMidpoint` — integers in USD
- `confidenceLevel` — integer 0–100
- `confidenceFactors` — object with keys: `image_quality`, `damage_visibility`, `model_identification`, `assessment_notes`
- `mode` — echoes back which mode was used
- `downloadLink` — always `null`

## Mode behavior
- `short`: reportContent is 3-5 sentences. Identifies vehicle, describes damage, states cost range and confidence. No tables or sections.
- `full`: reportContent is a full markdown document with damage tables, itemized cost breakdown, and insurance section.

## Underlying model behavior
The model is prompted to return a JSON object. `reportContent` is the `report_in_md_format` field from that JSON. Cost and confidence fields are extracted directly from the same JSON response. The model always returns all fields regardless of mode — only `reportContent` changes in length.

## Sample Payloads

### mode=short
```
POST /api/v1/assess
Content-Type: multipart/form-data

file=<image binary>
message=front bumper collision
mode=short
```

Expected response:
```json
{
  "success": true,
  "data": {
    "message": "front bumper collision",
    "mode": "short",
    "reportContent": "The vehicle is identified as a 2019 Toyota Corolla with front-end collision damage affecting the bumper cover, hood, and left headlight assembly. The bumper cover is cracked and displaced, the hood shows moderate deformation, and the headlight unit is shattered requiring full replacement. Estimated repair cost ranges from $2,100 to $2,850, with an estimated total of $2,450. Assessment confidence is HIGH (82%) based on clear image quality and full damage visibility.",
    "downloadLink": null,
    "costEstimateLow": 2100,
    "costEstimateHigh": 2850,
    "costEstimateMidpoint": 2450,
    "confidenceLevel": 82,
    "confidenceFactors": {
      "image_quality": "good",
      "damage_visibility": "clear",
      "model_identification": "certain",
      "assessment_notes": "All damaged areas fully visible, model confirmed via rear badge"
    }
  }
}
```

### mode=full
```
POST /api/v1/assess
Content-Type: multipart/form-data

file=<image binary>
message=front bumper collision
mode=full
```

Expected response:
```json
{
  "success": true,
  "data": {
    "message": "front bumper collision",
    "mode": "full",
    "reportContent": "## D.E.C.R.E.E — Damage Evaluation & Cost REpair Estimator\n\n**Claim Number:** 20240315-4821\n**Date:** 2024-03-15\n\n## Vehicle Identification\nToyota Corolla 2019 (C-segment sedan)\n\n## Damage Evaluation\n...(full markdown report with tables)...",
    "downloadLink": null,
    "costEstimateLow": 2100,
    "costEstimateHigh": 2850,
    "costEstimateMidpoint": 2450,
    "confidenceLevel": 82,
    "confidenceFactors": {
      "image_quality": "good",
      "damage_visibility": "clear",
      "model_identification": "certain",
      "assessment_notes": "All damaged areas fully visible, model confirmed via rear badge"
    }
  }
}
```

### Error — no file
```json
{ "error": "A file is required (multipart field name: \"file\")." }
```

### Error — server/model failure
```json
{ "success": false, "error": "Assessment failed." }
```

## Key constraints
- Images over 4.5 MB are auto-resized before being sent to the model
- The model expects a vehicle photo; non-vehicle images will produce unreliable output
- AWS credentials must be active on the host machine (CLI login)
