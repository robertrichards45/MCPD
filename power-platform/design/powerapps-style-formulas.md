# Power Apps styling formulas — approved MCPD Sentinel look

These are implementation patterns. Control names can change when the Canvas App is created.

## App background

```powerfx
ColorValue("#06111D")
```

## Sidebar background

```powerfx
ColorValue("#081725")
```

## Card fill

```powerfx
ColorValue("#0C1B2A")
```

## Raised card fill

```powerfx
ColorValue("#102235")
```

## Border

```powerfx
ColorValue("#1D3A52")
```

## Primary action

```powerfx
ColorValue("#147DFF")
```

Hover:

```powerfx
ColorValue("#3592FF")
```

## Text

Primary:

```powerfx
ColorValue("#F4F8FC")
```

Secondary:

```powerfx
ColorValue("#98AABD")
```

## Responsive sidebar

```powerfx
App.Width >= 1000
```

Desktop sidebar width:

```powerfx
If(App.Width >= 1000, 224, 0)
```

Main content X:

```powerfx
If(App.Width >= 1000, 224, 0)
```

Main content width:

```powerfx
Parent.Width - Self.X
```

## Responsive dashboard columns

```powerfx
If(
    App.Width >= 1400,
    4,
    App.Width >= 1000,
    3,
    App.Width >= 700,
    2,
    1
)
```

## Active navigation item

Fill:

```powerfx
If(
    gblCurrentModule = ThisItem.ModuleKey,
    ColorValue("#147DFF"),
    RGBA(0,0,0,0)
)
```

Text color:

```powerfx
ColorValue("#F4F8FC")
```

## Stale-data banner

```powerfx
If(
    DateDiff(ThisItem.LastVerifiedAt, Now(), TimeUnit.Hours) >
        Value(LookUp(AppConfigurations, ConfigKey="WatchDataStaleHours", ConfigValue)),
    "STALE — VERIFY",
    "Verified"
)
```

## Semantic status fill

```powerfx
Switch(
    ThisItem.Status,
    "Approved", ColorValue("#2BC66D"),
    "Completed", ColorValue("#2BC66D"),
    "Active", ColorValue("#2BC66D"),
    "Returned", ColorValue("#F2B84B"),
    "Overdue", ColorValue("#F05B63"),
    "Draft", ColorValue("#6E8297"),
    ColorValue("#37A7FF")
)
```

Use a text label with the status. Do not rely on this color alone.
