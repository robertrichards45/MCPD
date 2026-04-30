# CLEOC Desktop Setup

This gives you a domain-free CLEOC program that officers can launch from their desktops.

## What to use

- `launch_cleoc_desktop.cmd`
  Runs CLEOC only on the current PC at `http://127.0.0.1:8092/cleo/reports`

- `launch_cleoc_shared_host.cmd`
  Runs CLEOC on one shared host PC so other officers on the same network can use it

- `open_cleoc_officer_client.cmd`
  Opens the shared CLEOC host from an officer workstation

- `install_cleoc_desktop_shortcuts.ps1`
  Creates desktop shortcuts for the host and client launchers

## Important architecture note

If every officer runs their own separate local copy, they will each have separate data and separate logins.

If you want:

- the same officer accounts
- the same reports
- grading by supervisors
- multiple officers in the program at the same time

then you should run **one shared CLEOC host** on one PC and let officers connect to that host over the local network.

## One-time setup on the host PC

1. Open PowerShell in this folder.
2. Create the virtual environment:

```powershell
python -m venv .venv
```

3. Install requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

4. Run the shared host:

```powershell
.\launch_cleoc_shared_host.cmd
```

5. Tell officers to open:

```text
http://HOST-PC-NAME:8092/cleo/reports
```

Replace `HOST-PC-NAME` with the host computer name shown in the launcher window.

## Officer desktop setup

1. Copy `cleo_client.local.cmd.example` to `cleo_client.local.cmd`
2. Set:

```cmd
set CLEOC_CLIENT_URL=http://HOST-PC-NAME:8092/cleo/reports
```

3. Run:

```powershell
.\install_cleoc_desktop_shortcuts.ps1
```

4. Put the `CLEOC Officer Client` shortcut on each officer desktop.

## Local single-PC use

If one officer just wants CLEOC on their own machine only:

```powershell
.\launch_cleoc_desktop.cmd
```

## Notes

- No domain is required.
- The shared host must stay running while officers are connected.
- This setup is for LAN use, not internet exposure.
- The app opens directly to the CLEOC report workflow.
