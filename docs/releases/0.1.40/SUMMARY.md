# ServerOrchestration v0.1.40

- Fixed 3x-ui status persistence mismatch that was crashing on `update_3xui_status(...)` during console/subscription checks.
- Subscription checks now parse `Subscription-Userinfo` and related profile headers to surface traffic, expiry, and profile metadata.
- Probe history now stores human-readable SSL and 3x-ui details so operators can see certificate/subscription context directly in the UI.
