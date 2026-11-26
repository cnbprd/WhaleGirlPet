# Privacy policy

Last updated: 2026-11-26

## 3D core (signed artifact)

The 3D desktop pet (`whale3d.exe` and `WhaleGirlPet-3D-Setup-*.exe`) runs locally. It does **not** include telemetry, analytics, advertising, account registration, or cloud storage.

- The emotion bus binds only to `udp://127.0.0.1:47832`; datagrams stay on the local machine.
- Settings, model paths and window state are stored locally.
- The application does not contact the network on its own. If the user clicks a GitHub Releases or project link, the default browser opens that page.
- The installer writes only under `%LOCALAPPDATA%\WhaleGirlPet3D` and the Start Menu; it does not upload data.

## Historical 2D application

The archived PySide6 application has optional online features. They run only after the user configures or invokes them:

- cloud LLM / TTS / ASR API profiles: requests go to the endpoint and model the user configures; API keys are stored locally;
- weather and news panels: requests go to the configured public data source;
- update checks: requests go to GitHub Releases;
- local Ollama / local models: requests stay on `127.0.0.1`.

There is no background telemetry. Chat history, memory, audio cache, API profiles and configuration are stored in the user's local application data directory. Removing the application data directory removes them.

## Third-party components

The 3D build includes SDL3, ozz-animation, stb_image and nlohmann/json under their own licenses; they do not add network or telemetry behavior. See `3d/THIRD_PARTY_NOTICES.txt` and `LICENSE`.

## Contact

Privacy questions: open an issue at <https://github.com/cnbprd/WhaleGirlPet/issues>.
