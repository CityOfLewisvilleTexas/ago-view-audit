# audit_view_layer_edit_settings.py

Audits all hosted feature layer views in an ArcGIS Online organization and flags any
edit-related settings that deviate from a defined set of expected values. Only views
with one or more deviations are reported; views that fully match the expected settings
produce no output.

---

## Background

Hosted feature layer views in ArcGIS Online share the same underlying data as their
source feature layer — edits made through a view write directly to the source. Because
of this, it is important to ensure that views intended for read-only access do not have
editing, change tracking, or sync accidentally enabled.

This script was developed to support a periodic audit workflow for organizations that
maintain a standard for view layer settings.

---

## Requirements

| Requirement | Notes |
|---|---|
| Python 3.x | Standard ArcGIS Pro Python environment is sufficient |
| ArcGIS API for Python | Included with ArcGIS Pro; installable via `pip install arcgis` |
| ArcGIS Online account | Must have access to the organization being audited |

---

## Configuration

At the top of the script, two variables control behavior:

```python
PORTAL_URL = "https://www.arcgis.com"   # Change to your portal URL if using ArcGIS Enterprise
USERNAME   = None                        # See Authentication section below
```

The expected settings are defined in the `EXPECTED` dictionary:

```python
EXPECTED = {
    "editing_enabled":  False,   # Enable editing
    "change_tracking":  False,   # Keep track of changes (add/update/delete)
    "sync_enabled":     False,   # Enable sync
    "editor_tracking":  True,    # Keep track of who edited (informational only — see note below)
}
```

Modify these values if your organization's standards differ.

> **Note on `editor_tracking`:** This setting is inherited from the source feature layer
> and cannot be changed independently on a view. The script reads and reports it for
> informational purposes but never flags it as a deviation. To change it, update the
> setting on the source hosted feature layer.

---

## Authentication

The script supports several authentication approaches. Edit the entry point at the
bottom of the script to match your environment:

```python
# Option 1 — Active ArcGIS Pro session (recommended for Pro users)
gis = GIS("home")

# Option 2 — Prompt for password interactively
USERNAME = "your_username"
gis = GIS(PORTAL_URL, USERNAME)

# Option 3 — Fully scripted (use with caution; avoid hardcoding passwords in shared scripts)
gis = GIS(PORTAL_URL, "your_username", "your_password")
```

---

## How It Works

1. Connects to the ArcGIS Online organization using the configured credentials.
2. Searches for all items with the `"View Service"` type keyword — the reliable way to
   identify hosted feature layer views as distinct from primary hosted feature layers.
3. For each view, calls the feature service REST endpoint (`/FeatureServer?f=json`) via
   `FeatureLayerCollection.fromitem()` to retrieve the actual service-level properties.
   (`item.properties` returns portal item metadata, not service capabilities, and is not
   used for this purpose.)
4. Compares `capabilities` (editing, sync), `changeTrackingEnabled`, and
   `editorTrackingInfo` against the expected values.
5. Prints only views that have one or more deviations, along with the expected and
   actual value for each deviating setting.

---

## Example Output

```
Connected as: nick.doe
Portal:       https://www.arcgis.com

======================================================================
Searching for hosted feature layer views...
======================================================================
Found 398 view layer(s).

View: Stormwater Inlets (Public View)  [owner: nick.doe]
  Item ID: a1b2c3d4e5f6...
  • Enable editing:                   expected=False, actual=True
  • Keep track of changes (add/update/delete): expected=False, actual=True

View: Pavement Condition Survey View  [owner: jane.smith]
  Item ID: f6e5d4c3b2a1...
  • Enable sync:                      expected=False, actual=True

======================================================================
No views skipped - all item properties were accessible.
Audit complete. 3 setting deviation(s) found across 398 view(s).
======================================================================
```

If all views match the expected settings, the output will simply be:

```
======================================================================
No views skipped - all item properties were accessible.
Audit complete for all 398 view(s).
======================================================================
```

---

## Troubleshooting

**`[WARNING] Could not read service properties for '...'`**
The script could not connect to the feature service endpoint for that item. Common causes:
- The item is owned by another user and the service is not publicly accessible.
- The service has been deleted but the item record remains in the portal.
- A network or authentication issue prevented the REST request.

Skipped items are counted in the summary line at the end of the output.

**Fewer views returned than expected**
The `max_items=1000` parameter in the search call caps results at 1,000 items. If your
organization has more than 1,000 view layers, increase this value or add pagination logic.

**Running in a Jupyter Notebook (ArcGIS Online or ArcGIS Pro)**
Replace the entry point block with:
```python
gis = GIS("home")
audit_views(gis)
```