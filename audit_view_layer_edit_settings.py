"""
from Claude: https://claude.ai/share/3b425f2a-6752-4f7e-bb42-9b8ee99babc8
audit_view_layer_edit_settings.py

Audits all hosted feature layer views in your ArcGIS Online organization
and flags any edit-related settings that deviate from expected values.

Expected settings:
  - Enable editing:                False
  - Keep track of changes (add/update/delete): False
  - Keep track of editor (name/date):          True  (inherited from source — reported only)
  - Enable sync:                   False
"""

from arcgis.gis import GIS

# ── Configuration ─────────────────────────────────────────────────────────────
# TODO move global variables to .env file and add .env.example file
PORTAL_URL = "https://www.arcgis.com"   # or your portal URL
USERNAME   = None   # set to a string to prompt for a specific user,
                    # or None to use active Pro session / env credentials

# Expected values — change these if your org standards differ
EXPECTED = {
    "editing_enabled":    False,
    "change_tracking":    False,
    "sync_enabled":       False,
    # editor_tracking is inherited/read-only on views; we report it but don't flag it as a "problem"
    "editor_tracking":    True,
}
# ──────────────────────────────────────────────────────────────────────────────

def get_layer_capabilities(item):
    """
    Pull editing-related capabilities directly from the feature service REST endpoint
    via FeatureLayerCollection. item.properties returns portal item metadata, NOT
    service-level properties — capabilities, changeTrackingEnabled, etc. live on the service.
    """
    try:
        from arcgis.features import FeatureLayerCollection
        flc = FeatureLayerCollection.fromitem(item)
        svc_props = flc.properties  # This hits /FeatureServer?f=json

        # capabilities is a comma-separated string at the service level
        capabilities_str = svc_props.get("capabilities", "") or ""
        capabilities = [c.strip().lower() for c in capabilities_str.split(",") if c.strip()]

        editing_enabled = "editing" in capabilities
        sync_enabled    = "sync" in capabilities

        change_tracking = bool(svc_props.get("changeTrackingEnabled", False))

        eti = svc_props.get("editorTrackingInfo", {})
        editor_tracking = bool(eti.get("enableEditorTracking", False))

        return {
            "editing_enabled": editing_enabled,
            "change_tracking": change_tracking,
            "sync_enabled":    sync_enabled,
            "editor_tracking": editor_tracking,
        }

    except Exception as e:
        print(f"    [WARNING] Could not read service properties for '{item.title}': {e}")
        return None
        

def audit_views(gis):
    """Search for all hosted feature layer views and audit their settings."""
    print(f"\nConnected as: {gis.users.me.username}")
    print(f"Portal:       {gis.url}\n")
    print("=" * 70)
    print("Searching for hosted feature layer views...")
    print("=" * 70)

    # Search for all view items — 'View Service' typekeyword flags views
    items = gis.content.search(
        query='typekeywords:"View Service"',
        item_type="Feature Layer",
        max_items=1000
    )

    if not items:
        print("No hosted feature layer views found.")
        return

    print(f"Found {len(items)} view layer(s).\n")

    issues_found = 0
    skipped = 0

    for item in items:
        current = get_layer_capabilities(item)
        if current:
            # ── Collect deviations ────────────────────────────────────────────────
            deviations = []
    
            if current["editing_enabled"] != EXPECTED["editing_enabled"]:
                deviations.append(
                    f"  • Enable editing:                   "
                    f"expected={EXPECTED['editing_enabled']}, "
                    f"actual={current['editing_enabled']}"
                )
    
            if current["change_tracking"] is not None and \
               current["change_tracking"] != EXPECTED["change_tracking"]:
                deviations.append(
                    f"  • Keep track of changes (add/update/delete): "
                    f"expected={EXPECTED['change_tracking']}, "
                    f"actual={current['change_tracking']}"
                )
    
            if current["sync_enabled"] != EXPECTED["sync_enabled"]:
                deviations.append(
                    f"  • Enable sync:                      "
                    f"expected={EXPECTED['sync_enabled']}, "
                    f"actual={current['sync_enabled']}"
                )
    
            # Editor tracking is inherited — always report its value as informational
            editor_tracking_note = (
                f"  ℹ  Editor tracking (inherited, read-only on view): "
                f"{current['editor_tracking']}"
            )
    
            # ── Report ────────────────────────────────────────────────────────────
            if deviations:
                owner_info = f"[owner: {item.owner}]"
                print(f"View: {item.title}  {owner_info}")
                print(f"  Item ID: {item.id}")
                issues_found += len(deviations)
                for d in deviations:
                    print(d)

        else:
            print("Skipping item without properties.")
            skipped += 1

    print("=" * 70)
    if skipped:
        print(f"Skipped {skipped} view(s) as item properties were not accessible.")
    else:
        print("No views skipped - all item properties were accessible.")
    if issues_found:
        print(f"Audit complete. {issues_found} setting deviation(s) found across {len(items)} view(s).")
    else:
        print(f"Audit complete for all {len(items)} view(s).")
    print("=" * 70)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if USERNAME:
        gis = GIS(PORTAL_URL, USERNAME)       # will prompt for password
    else:
        gis = GIS("home")

    audit_views(gis)