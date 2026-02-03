"""
Shop data - Accessory definitions for the owl customization system.
"""

# Available accessory slots on the owl
SLOTS = ["head", "eyes", "neck", "back"]

# Accessory definitions
# Each accessory has: name, price, slot, and emoji (for display)
ACCESSORIES = {
    # Head items
    "grad_cap": {
        "name": "Graduation Cap",
        "price": 50,
        "slot": "head",
        "emoji": "🎓",
        "description": "For the scholarly owl!"
    },
    "crown": {
        "name": "Royal Crown",
        "price": 100,
        "slot": "head",
        "emoji": "👑",
        "description": "Rule the math kingdom!"
    },
    "wizard_hat": {
        "name": "Wizard Hat",
        "price": 75,
        "slot": "head",
        "emoji": "🧙",
        "description": "Math is basically magic."
    },
    "party_hat": {
        "name": "Party Hat",
        "price": 15,
        "slot": "head",
        "emoji": "🎉",
        "description": "Every solved problem is a party!"
    },
    "detective_hat": {
        "name": "Detective Hat",
        "price": 45,
        "slot": "head",
        "emoji": "🕵️",
        "description": "Solve math mysteries."
    },

    # Eye items
    "sunglasses": {
        "name": "Cool Sunglasses",
        "price": 30,
        "slot": "eyes",
        "emoji": "😎",
        "description": "Too cool for school."
    },
    "nerdy_glasses": {
        "name": "Nerdy Glasses",
        "price": 20,
        "slot": "eyes",
        "emoji": "🤓",
        "description": "Big brain energy."
    },
    "star_glasses": {
        "name": "Star Glasses",
        "price": 40,
        "slot": "eyes",
        "emoji": "⭐",
        "description": "You're a math star!"
    },

    # Neck items
    "red_bow_tie": {
        "name": "Red Bow Tie",
        "price": 25,
        "slot": "neck",
        "emoji": "🎀",
        "description": "Fancy and smart."
    },
    "scarf": {
        "name": "Winter Scarf",
        "price": 35,
        "slot": "neck",
        "emoji": "🧣",
        "description": "Stay cozy while studying."
    },
    "gold_medal": {
        "name": "Gold Medal",
        "price": 60,
        "slot": "neck",
        "emoji": "🏅",
        "description": "Math champion!"
    },

    # Back items
    "wings": {
        "name": "Angel Wings",
        "price": 150,
        "slot": "back",
        "emoji": "👼",
        "description": "Fly through equations."
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
