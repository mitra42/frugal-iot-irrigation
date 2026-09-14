# `data/` - files uploaded to the device's own filesystem

Everything here is copied onto the device with:

    pio run --target uploadfs --environment ff_openmppt

It is **not** part of the firmware, so changing a WiFi password does not mean recompiling.

## `data/wifi/`

One file per network. The **file name** is the network name (SSID) and the **contents** are the
password. A device tries every network it finds a file for, so you can leave several here.

    data/wifi/MyHomeWiFi          <- a file containing the password, nothing else

## `data/frugal_iot/`

Device settings, one file per setting. The commonest are `organization`, `project` and
`device_id`, which decide where the device's readings appear.

Both directories are in `.gitignore`, because they hold passwords. This README is not.
