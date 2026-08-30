"""Constants for the Motion Blinds integration."""

STATE_ON = "ON"
STATE_UNAVAILABLE = "UNAVAILABLE"

KEY_LENGTH = 16
DEFAULT_MAX_ANGLE = 180
CLOSED_THRESHOLD_POSITION = 100
CLOSED_THRESHOLD_TILT = 95

# Blind types (motionblinds BlindType names) that support tilt in addition to position.
TILT_TYPES = {
    "VenetianBlind",
    "ShangriLaBlind",
    "DoubleRoller",
    "DualShade",
    "VerticalBlind",
    "VerticalBlindLeft",
    "VerticalBlindRight",
    "RollerTiltMotor",
    "WoodShutter",
}

# Blind types that only support tilt (no position).
TILT_ONLY_TYPES = {
    "WoodShutter",
}

# Position-preset select options (UC convention: 0 = closed, 100 = open).
SELECT_FAVORITE = "Favourite"
POSITION_PRESETS = {"Open": 100, "75%": 75, "50%": 50, "25%": 25, "Closed": 0}
SELECT_OPTIONS = ["Open", "75%", "50%", "25%", "Closed", SELECT_FAVORITE]

# Remote simple-command actions applied across every blind on the gateway.
ALL_OPEN = "ALL_OPEN"
ALL_CLOSE = "ALL_CLOSE"
ALL_STOP = "ALL_STOP"
