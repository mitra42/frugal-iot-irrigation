# `data/` - files uploaded to the device's own filesystem

Everything here is copied onto the device with:

    pio run --target uploadfs --environment ff_openmppt

It is **not** part of the firmware, so changing a WiFi password does not mean recompiling.

## The layout: one flat file per setting

Every file sits directly in `data/`, named `<module>.<setting>`, and its contents are the value.
There are no subdirectories - on LittleFS each directory costs a whole 8KB block, which filled the
filesystem on small boards. (A board still holding the old `wifi/`, `frugal_iot/` directories
converts them to this layout by itself, once, at boot.)

Two characters in a name have to be written as codes, because `.` separates the parts:

| In the real name | Write it as |
|---|---|
| `.` | `%2E` |
| `%` | `%25` |

### `wifi.<network name>`

One file per network. The rest of the **file name** is the network name (SSID) and the
**contents** are the password, nothing else - no newline at the end. A device tries every network
it finds a file for, so you can leave several here.

    data/wifi.MyHomeWiFi            <- contains the password
    data/wifi.Cafe 2%2E4G           <- the network called "Cafe 2.4G"

### `frugal_iot.<setting>`

Device settings. The commonest are `project` and `description`, which decide where the device's
readings appear and what it is called on the dashboard.

    data/frugal_iot.project         <- e.g. lotus
    data/frugal_iot.description     <- e.g. Irrigation north field

Any other setting saved from the dashboard is stored the same way - `mppt.automatic`, for example.
You can put one here to have a board start with it.

Every `wifi.*` and `frugal_iot.*` file is in `.gitignore`, because they hold passwords and
site details. This README is not.
