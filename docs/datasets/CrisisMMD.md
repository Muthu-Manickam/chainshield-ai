---
type: dataset
licence: CC BY-NC-SA 4.0 (per Hugging Face card; original terms page unreachable)
---
# CrisisMMD v2.0 (text only)

- Source: https://huggingface.co/datasets/QCRI/CrisisMMD (original: crisisnlp.qcri.org)
- 16,058 tweets from seven 2017 events (Irma, Maria, Harvey, California wildfires, Mexico earthquake, Sri Lanka floods, Iraq-Iran earthquake).
- Informative 11,509 / not informative 4,549. Humanitarian 8 classes; vehicle damage (54) and missing/found (40) are too small, merge them.
- Use `label_text` from the original files; the Hugging Face `label` field is not the text label.
- Official split 11,584 / 2,237 / 2,237 tweets. See [[ADR-011 CrisisMMD split]].
- Non-commercial: never commit tweet text to a public place.
