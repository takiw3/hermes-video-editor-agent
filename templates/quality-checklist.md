# Quality checklist

Used by `edit-quality-review`. Each line is pass or fail with the timecode or frame as evidence. A zero exit code proves the process finished. Only inspection proves the rest.

Render: `<file>` · SHA-256: · Receipt: · Stage: `<draft | final>` · Reviewed against: paper edit, style decision, brand identity, transcript, export preset

| # | Check | Result | Evidence (timecode or frame) |
| --- | --- | --- | --- |
| 1 | The file exists and its SHA-256 matches the receipt |  |  |
| 2 | Duration, resolution, frame rate, codec match the export preset |  |  |
| 3 | The opening delivers the hook `social-media` wrote |  |  |
| 4 | Every cut in the edit decision list is present and lands on its timecode |  |  |
| 5 | No cut changes the meaning of a sentence |  |  |
| 6 | Captions match the verified transcript, word for word |  |  |
| 7 | No on-screen words the speaker did not say, unless listed as owner-approved |  |  |
| 8 | Text is readable, inside the recorded safe zone, with checked contrast |  |  |
| 9 | Overlays use the brand identity and carry only approved claims |  |  |
| 10 | Audio is present, not silent, and does not clip (measured) |  |  |
| 11 | Speech is intelligible over music at every moment |  |  |
| 12 | Color treatment matches the approved look (before and after sheets) |  |  |
| 13 | Each requested aspect ratio is its own reviewed render |  |  |
| 14 | Every asset has a complete rights record |  |  |
| 15 | Consent is recorded for every identifiable person, client, and minor |  |  |
| 16 | Any sponsorship disclosure in the script or brief is intact |  |  |
| 17 | Nothing from a reference video is in the file |  |  |
| 18 | Source footage checksums are unchanged (`hf.py footage-verify`) |  |  |
| 19 | The style decision on the receipt matches the one the approver made |  |  |
| 20 | Status is stated exactly: a draft is a draft, a final is not approved, an approved file is not posted |  |  |

Frames inspected (denser at the opening and at every cut near speech):

Not checked, and why:

Overall: `<pass | fail>`. A render that fails review is reported as `draft rendered` with the failing timecodes.
