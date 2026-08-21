# X2D managed integration update

This release packages the X2D/Bambuddy integration as an automatic, checksum-pinned update for FilaMan.

- Bambuddy plugin: `1.3.8`
- Plugin source: `c2c1ad390e6a7f64174185802a6408d884318083`
- Plugin ZIP SHA256: `a41f6bd38f9ebce1f21b620f9ce7ea8ab3984fc2a633cffe18e33518e906d508`
- The plugin is verified and installed/upgraded before printer drivers start.
- A newer installed plugin is never downgraded automatically.
- Plugin upgrades use same-filesystem staging and rollback so dependency or database failures preserve the previous working plugin.
- Existing persistent FilaMan data and printer configuration are retained.

For the X2D acceptance configuration, keep the Bambuddy driver in inventory-only printer-write mode. Cloud/Handy connectivity remains the printer's source of truth for physical material configuration while FilaMan tracks logical inventory and print consumption.
