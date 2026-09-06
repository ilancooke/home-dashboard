"""Human-readable audio labels that can be customized for this home."""

HARDWARE_ZONES = (1, 2, 3, 4, 5, 6)

# Only these zones appear on the dashboard. Zones 5 and 6 remain available
# through the API for future use, but are not installed in the current UI.
VISIBLE_ZONES = (1, 2, 3, 4)

ZONE_NAMES = {
    1: "Lounge",
    2: "Master Bathroom",
    3: "Patio",
    4: "Living Room",
}

SOURCE_NAMES = {
    1: "Echo Dot",
    2: "Patio TV",
    3: "Input 3",
    4: "Input 4",
    5: "Input 5",
    6: "Living Room TV",
}
