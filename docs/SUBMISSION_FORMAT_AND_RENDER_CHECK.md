# Submission PDF Format and Render Check

**Candidate:** `output/pdf/ColluScope_Submission_Candidate_2026-10-20.pdf`<br>
**Markdown source:** `submission-prep/paper.md` (canonical source for the candidate PDF).<br>
**Date:** 2026-10-20. This is an AI-assisted, pre-sprint review candidate, not a submission-ready entrant-authored report.

## Automated format checks

- Abstract word count: recorded by `scripts/build_submission_pdf.py`; maximum official limit: 150 words.
- Page count and US Letter size: recorded from `pdfinfo`; target is 4-8 pages per the official recommendation, not a hard page cap.
- PDF file size: recorded from `pdfinfo`; official upload limit: 25 MB.
- PDF text extraction: check all section headings, references, figure captions, author placeholders, and appendix title.
- Link annotations: all cited DOI/arXiv/Apart URLs must be clickable and match visible reference targets.
- Fonts and render: `pdffonts`, `pdftoppm`, and per-page PNG review. Poppler emitted missing-display-font warnings for Symbol and ArialUnicode during rendering, while the resulting pages remained legible; this is recorded for review rather than silently ignored.
- Exact template: not verified. The official Google Docs copy link redirected to Google sign-in. The current PDF uses a reproducible ReportLab layout with the recommended sections and length, but it must be transferred into the official template if the organizers confirm that template is mandatory.
- Author fields: placeholders remain; submission requirement not yet satisfied.

## Visual inspection

Review every page image in `tmp/pdfs/submission-candidate/` after the last PDF build. Check title/abstract, table legibility, M1/M2/M3 figures, page breaks, appendix heading, references, URL wrapping, and page numbers. The first visual review found the M3 paragraph split across pages 4-5 and the M2 chart needed a wider layout. The PDF builder now caps only the M3 plot height to prevent that orphaned paragraph while retaining full-width M2 figures. Re-render and record whether the paragraph now stays together and all five pages remain legible.

## Build and diagnostic history

1. Built-in Codex LaTeX project compiler successfully compiled the editable `submission-prep/main.tex` before the final editorial-status wording update. This is a source sanity check only; it is not the delivered PDF engine.
2. A direct MiKTeX `pdflatex` run entered a package-install dialog and stalled because the environment lacked required packages. No package install was accepted. The raw diagnostics are preserved in `docs/results/submission-prep/pdflatex-pass1.log` and `pdflatex-pass2.log`; the environment displayed a Windows-version compatibility message. This is a failed LaTeX CLI attempt, not a paper or data failure.
3. The deliverable PDF is built by the local ReportLab script, not by MiKTeX. The failed LaTeX attempt is retained and not erased from the history.

## Final check record

Final PDF rebuild: 2026-10-20.

- Abstract: 138 words.
- Pages: 5 US Letter pages; within the official 4-8-page recommendation.
- File size: 419,690 bytes, below the official 25 MB upload limit.
- PDF SHA-256: `1318bf2ce0f1588256e45218e8f369ecfb83b303dff4293b32601537410a16c2`.
- Source Markdown SHA-256: `35f2f96e33e83f302d1936f340376e652941b7cc9453384278a62371ccb15f14`.
- Four embedded raster figures detected on pages 3-4; page PNGs 1-5 were visually inspected. The 2 M2 charts and M3 chart have legible labels/captions; no clipping or orphaned M3 paragraph remains. References and appendix appear on page 5; all five reference URLs have live link annotations.
- Text-object fonts detected by pdfplumber: Helvetica, Helvetica-Bold, Helvetica-Oblique. The current `pdffonts` resolves to MiKTeX and failed on registry access in this environment; text extraction and visual rendering succeeded. Poppler warned about Symbol/ArialUnicode display fonts; the five rendered page PNGs were visually legible.
- PDF structural validator: `scripts/validate_submission_pdf.py` returned `PASS_STRUCTURAL_CHECKS`, 5 pages, 4 images, 5 URLs. Its JSON output is `docs/results/submission-prep/pdf-validation.json`.
- Updated LaTeX source compiled successfully with the built-in Codex editor compiler. The ReportLab-built PDF remains the delivered artifact.

Exact-template, actual author/affiliation, current submission-form status, entrant eligibility and new Sprint-time result blockers remain open. This PDF is an AI-assisted review candidate and is not ready to submit verbatim.

## Latest deterministic rebuild and final visual review (2026-10-20)

The preceding records are retained as earlier build history. An initial rerun exposed that ReportLab's default creation timestamp changed the PDF hash despite identical page pixels. The builder now freezes `SOURCE_DATE_EPOCH` to 2026-10-20T00:00:00Z. Two independent builds with the same source and environment produced byte-identical outputs; the corrected final PDF was then rebuilt and validated. The canonical Markdown states that A and B each receive the private +20 rule and that successful delivery does not establish comprehension.

- Current PDF SHA-256: `826a90742690ce88644a1b07e5bc35c48804a4c2611ab7d10394c8b62452f1cd`.
- Current PDF size: 419,761 bytes; 5 US Letter pages; abstract: 138 words.
- Current Markdown SHA-256: `edbabbac2d15e94bf3e5fe0dae05b65b0939f3c6cd34aa859f46b851362c098d`.
- Current LaTeX source SHA-256: `342c414f4deb37033196645193ce3a5d2feeb1ef5afa42cd162d4d2cb488de1a`.
- The latest page images in `tmp/pdfs/submission-candidate-final-r6/` were compared pixel-by-pixel against all five individually reviewed `final-r3` pages; every page is identical. Title, table, all four figures, captions, section flow, appendix, references, links, and page numbers are legible; no clipping or split M3 paragraph was found. Poppler still emits missing display-font warnings for Symbol and ArialUnicode, but the rendered pages remain legible.
- The final structural validation is `docs/results/submission-prep/pdf-validation.json`; it reports 5 pages, 4 embedded figures and all 5 required clickable links. The LaTeX source was compiled after the wording update. The PDF itself remains built with ReportLab.
- `docs/results/submission-prep/submission_manifest.json` records 90 deliverable/source/evidence hashes; `manifest-verification.json` independently verified all hashes, sizes, the PDF-validator hash link, and exclusion of private M3 raw paths. The verification JSON is deliberately not self-inventoried.
- Byte-reproducibility logs for the final source are `pdf-final-repro-build-a.log`, `pdf-final-repro-build-b.log`, and `pdf-final-repro-check.log` in `docs/results/submission-prep/`; final validation and page-render parity are in `pdf-validation-final-frozen.log` and `pdf-render-final-frozen-parity.log`. The malformed one-off comparison command is retained in `pdf-render-final-r3.log`; its corrected reusable script is `scripts/compare_submission_page_renders.py`.

This corrects the earlier hash/size above without deleting the prior build record. Exact official-template matching and author fields remain unresolved; this remains a review candidate, not a submission file.

## Positive-control disclosure revision (2026-10-20)

The Limitations appendix now states that M0-M3 contains no behavior or reference positive-control condition and that a synthetic audit canary would validate code only. This follows the current official page's Results guidance; it does not claim that an unrun control was completed.

- Current PDF SHA-256: `1c4ff8ff98f94d28209e012d7ca18d3f7327e1e24cdf0fa28b37ed3a1878bfea` (419,915 bytes).
- Canonical Markdown SHA-256: `3add96d61c0eb7da131bbc0a14d9018089a6be1f6bedbe7a289466ce2b14f32c`.
- Editable LaTeX source SHA-256: `f28ae3c2909388bafee5815b58bfc1269e9597b00276005d5f8afbc6e7220cd6`; the desktop editor compiler reported success.
- Structural validation: `PASS_STRUCTURAL_CHECKS`; 5 US Letter pages, 138 abstract words, 4 images, 5 links. Two deterministic PDF builds were byte-identical.
- Visual QA: all five pages were rendered and inspected. A second render matched all five page images pixel-for-pixel. The appendix fits on page 5; no clipping or new page break was introduced. Poppler still reports missing display fonts for Symbol and ArialUnicode, but all rendered text is legible.
- Evidence logs: `expansion-review-pdf-build-a.log`, `expansion-review-pdf-build-b.log`, `expansion-review-pdf-validation.log`, `expansion-review-render.log`, `expansion-review-page-parity.log`, `expansion-review-claim-audit.log`, `expansion-review-scenario-check.log`, and `expansion-review-group-check.log` under `docs/results/submission-prep/`.
- The refreshed evidence manifest contains 112 inventoried files and passed independent hash/size/privacy-path verification with `model_calls=0`; its manifest hash is recorded in the companion, intentionally excluded `manifest-verification.json`.
