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
