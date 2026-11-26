# Code signing policy

**Free code signing provided by [SignPath.io](https://signpath.io/), certificate by [SignPath Foundation](https://signpath.org/).**

## Scope

This policy covers the Windows artifacts built from this repository's 3D mainline:

- `whale3d.exe` (the SDL3/OpenGL desktop pet)
- `WhaleGirlPet-3D-Setup-<version>.exe` (the Inno Setup installer)
- the release ZIP that contains the signed `whale3d.exe`

The 2D PySide6 tree and its historical installers are archived and are not part of a new SignPath signing request unless this policy is explicitly extended.

## Team roles

| Role | Member | Responsibility |
|---|---|---|
| Author | [cnbprd](https://github.com/cnbprd) (repository owner) | May modify source and build scripts |
| Reviewer | [cnbprd](https://github.com/cnbprd) | Reviews changes from non-committers before merge |
| Approver | [cnbprd](https://github.com/cnbprd) | Approves each signing request for a release |

All team members must use multi-factor authentication for GitHub and SignPath. The project is maintained by its owner; there is no separate commercial dual-licensing or closed-source component.

## Build and metadata

- Source and build scripts are public: `3d/build.ps1`, `3d/main.cpp`, `3d/model.cpp`, `3d/shell_ui.cpp`, `3d/emotion_bus.cpp`, `3d/whale3d.rc`, and `installer/whale3d.iss` / `installer/build_3d_installers.ps1`.
- The signed executable carries the product name `WhaleGirlPet`, product version `3.1.0.0`, file description `WhaleGirl 3D desktop pet`, and original filename `whale3d.exe`.
- The Inno Setup installer uses product name `鲸鱼娘 3D` and the same version as the release tag; its version metadata is set in `installer/whale3d.iss`.
- Signing order: sign `whale3d.exe` before packaging, compile the installer from the signed payload, then sign the installer and regenerate `.sha256`.

## Privacy

**This program will not transfer any information to other networked systems unless specifically requested by the user or the person installing or operating it.**

The signed 3D core does not include telemetry, analytics, advertising, or a cloud account. Its only network surface is:

- the local loopback emotion bus (`udp://127.0.0.1:47832`), which never leaves the machine; and
- user-initiated links to GitHub Releases or the project page.

The historical 2D application contains optional cloud AI, weather, and update features; those are documented in `PRIVACY.md` and are not part of the 3D core signing scope.

## Release approval

Every SignPath signing request must be approved by the Approver before the signed asset is uploaded. Unsigned artifacts must not be described as signed. Verification uses `Get-AuthenticodeSignature` and the adjacent `.sha256` file.
