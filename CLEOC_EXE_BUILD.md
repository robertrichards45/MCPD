# CLEOC Packaged EXE Build

This project can now be built into a Windows desktop app bundle using PyInstaller.

## What it produces

Running the build script creates:

```text
dist\CLEOC Desktop\
```

Inside that folder, the main program is:

```text
CLEOC Desktop.exe
```

## Build steps

From this project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\build_cleoc_exe.ps1
```

## Runtime behavior

The packaged app:

- starts a local CLEOC server
- opens the browser to `http://127.0.0.1:8092/cleo/reports`
- stores its local data in:

```text
%LOCALAPPDATA%\MCPD-CLEOC-Desktop
```

That includes:

- the SQLite database
- uploaded files
- report-related local storage

## Sharing the EXE

You can copy the whole folder:

```text
dist\CLEOC Desktop\
```

to another officer desktop or a shared drive.

Do not copy only the `.exe` by itself. Keep the full folder together.

## Important limitation

This packaged `.exe` is best for **single-PC local use**.

If each officer runs their own packaged copy, each officer will have:

- separate local data
- separate local logins
- separate report history

If you want everyone using the same reports and same logins at the same time, use the **shared host** setup instead of separate EXEs.
