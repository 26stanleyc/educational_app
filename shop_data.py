"""
Shop data - Accessory definitions for the owl customization system.
"""

# Available accessory slots on the owl
SLOTS = ["head", "eyes", "neck", "back"]

# Original prices (saved for later):
# grad_cap: 50, crown: 100, wizard_hat: 75, party_hat: 15, detective_hat: 45
# sunglasses: 30, nerdy_glasses: 20, star_glasses: 40
# bow_tie: 25, scarf: 35, medal: 60
# cape: 80, wings: 90, backpack: 35

# Accessory definitions
# Each accessory has: name, price, slot, and emoji (for display)
ACCESSORIES = {
    # Head items
    "grad_cap": {
        "name": "Graduation Cap",
        "price": 0,
        "slot": "head",
        "emoji": "🎓",
        "description": "For the scholarly owl!"
    },
    "crown": {
        "name": "Royal Crown",
        "price": 0,
        "slot": "head",
        "emoji": "👑",
        "description": "Rule the math kingdom!"
    },
    "wizard_hat": {
        "name": "Wizard Hat",
        "price": 0,
        "slot": "head",
        "emoji": "🧙",
        "description": "Math is basically magic."
    },
    "party_hat": {
        "name": "Party Hat",
        "price": 0,
        "slot": "head",
        "emoji": "🎉",
        "description": "Every solved problem is a party!"
    },
    "detective_hat": {
        "name": "Detective Hat",
        "price": 0,
        "slot": "head",
        "emoji": "🕵️",
        "description": "Solve math mysteries."
    },

    # Eye items
    "sunglasses": {
        "name": "Cool Sunglasses",
        "price": 0,
        "slot": "eyes",
        "emoji": "😎",
        "description": "Too cool for school."
    },
    "nerdy_glasses": {
        "name": "Nerdy Glasses",
        "price": 0,
        "slot": "eyes",
        "emoji": "🤓",
        "description": "Big brain energy."
    },
    "star_glasses": {
        "name": "Star Glasses",
        "price": 0,
        "slot": "eyes",
        "emoji": "⭐",
        "description": "You're a math star!"
    },

    # Neck items
    "bow_tie": {
        "name": "Red Bow Tie",
        "price": 0,
        "slot": "neck",
        "emoji": "🎀",
        "description": "Fancy and smart."
    },
    "scarf": {
        "name": "Winter Scarf",
        "price": 0,
        "slot": "neck",
        "emoji": "🧣",
        "description": "Stay cozy while studying."
    },
    "medal": {
        "name": "Gold Medal",
        "price": 0,
        "slot": "neck",
        "emoji": "🏅",
        "description": "Math champion!"
    },

    # Back items
    "cape": {
        "name": "Super Cape",
        "price": 0,
        "slot": "back",
        "emoji": "🦸",
        "description": "Math superhero!"
    },
    "wings": {
        "name": "Angel Wings",
        "price": 0,
        "slot": "back",
        "emoji": "👼",
        "description": "Fly through equations."
    },
    "backpack": {
        "name": "School Backpack",
        "price": 0,
        "slot": "back",
        "emoji": "🎒",
        "description": "Ready for class!"
    },
}


def get_accessories_by_slot(slot: str) -> dict:
    """Get all accessories for a specific slot."""
    return {k: v for k, v in ACCESSORIES.items() if v["slot"] == slot}


def get_accessory(item_id: str) -> dict:
    """Get a specific accessory by ID."""
    return ACCESSORIES.get(item_id, {})


def get_all_accessories() -> dict:
    """Get all accessories."""
    return ACCESSORIES
