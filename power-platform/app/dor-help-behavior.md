# DOR rating guidance behavior

The digital DOR should make the standardized evaluation guidance available without forcing the FTO to leave the form.

## Desktop

Each category row contains:
- category number;
- category name;
- 1–7 controls;
- N/O control;
- help/info icon;
- optional comment indicator.

Selecting the help icon opens a side panel showing:
- **1 — Unacceptable**
- **4 — Acceptable**
- **7 — Superior**

The text is populated from `fto-rating-anchors.csv`.

## Tablet/mobile

The row becomes a category card. The anchor guidance expands below the rating controls.

## Rating behavior

- 1, 4, and 7 display the manual anchor wording/summaries.
- 2, 3, 5, and 6 are intermediate ratings.
- N/O means the category was not observed.
- A rating is never auto-finalized by the application.
- Scenario-generated competency scores may populate a **draft recommendation only**.
- The FTO must select/finalize the DOR rating.
- Low ratings should prompt the FTO to consider/document remedial training; they do not automatically impose remediation.

## Power Fx pattern

```powerfx
Set(
    gblRatingAnchor,
    LookUp(
        FtoratingAnchors,
        CategoryNumber = ThisItem.CategoryNumber
    )
)
```

Help panel labels:

```powerfx
gblRatingAnchor.Rating1_Unacceptable
```

```powerfx
gblRatingAnchor.Rating4_Acceptable
```

```powerfx
gblRatingAnchor.Rating7_Superior
```
