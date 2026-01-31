"""
Firebase configuration and helper functions for authentication and database operations.
"""

import os
import pyrebase
import streamlit as st
from typing import Optional, Dict, List, Any


def get_firebase_config() -> Dict[str, str]:
    """Get Firebase configuration from Streamlit secrets or environment variables."""
    # Try environment variables first (Railway deployment)
    api_key = os.environ.get("FIREBASE_APIKEY")
    if api_key:
        return {
            "apiKey": api_key,
            "authDomain": os.environ.get("FIREBASE_AUTHDOMAIN", ""),
            "databaseURL": os.environ.get("FIREBASE_DATABASEURL", ""),
            "projectId": os.environ.get("FIREBASE_PROJECTID", ""),
            "storageBucket": os.environ.get("FIREBASE_STORAGEBUCKET", ""),
            "messagingSenderId": os.environ.get("FIREBASE_MESSAGINGSENDERID", ""),
            "appId": os.environ.get("FIREBASE_APPID", ""),
        }

    # Try Streamlit secrets (local development)
    try:
        return {
            "apiKey": st.secrets["firebase"]["apiKey"],
            "authDomain": st.secrets["firebase"]["authDomain"],
            "databaseURL": st.secrets["firebase"]["databaseURL"],
            "projectId": st.secrets["firebase"]["projectId"],
            "storageBucket": st.secrets["firebase"]["storageBucket"],
            "messagingSenderId": st.secrets["firebase"]["messagingSenderId"],
            "appId": st.secrets["firebase"]["appId"],
        }
    except Exception:
        pass

    # No config found
    return {}


@st.cache_resource
def init_firebase():
    """Initialize Firebase app. Cached to avoid re-initialization."""
    config = get_firebase_config()
    if not config or not config.get("apiKey"):
        return None
    try:
        return pyrebase.initialize_app(config)
    except Exception as e:
        print(f"Firebase initialization error: {e}")
        return None


def get_auth():
    """Get Firebase auth instance."""
    firebase = init_firebase()
    if firebase:
        return firebase.auth()
    return None


def get_db():
    """Get Firebase database instance."""
    firebase = init_firebase()
    if firebase:
        return firebase.database()
    return None


def sign_up(email: str, password: str, name: str) -> Dict[str, Any]:
    """
    Create a new user account.

    Returns:
        Dict with 'success', 'user_id', 'message' keys
    """
    auth = get_auth()
    db = get_db()

    if not auth or not db:
        return {"success": False, "user_id": None, "message": "Firebase not configured"}

    try:
        # Create user in Firebase Auth
        user = auth.create_user_with_email_and_password(email, password)
        user_id = user['localId']

        # Initialize user data in database
        user_data = {
            "name": name,
            "email": email,
            "currency": 0,
            "solved_questions": 0,
            "inventory": [],
            "equipped": {
                "head": None,
                "eyes": None,
                "neck": None,
                "back": None
            }
        }
        db.child("users").child(user_id).set(user_data)

        return {
            "success": True,
            "user_id": user_id,
            "id_token": user['idToken'],
            "message": "Account created successfully!"
        }
    except Exception as e:
        error_msg = str(e)
        if "EMAIL_EXISTS" in error_msg:
            return {"success": False, "user_id": None, "message": "This email is already registered."}
        elif "WEAK_PASSWORD" in error_msg:
            return {"success": False, "user_id": None, "message": "Password should be at least 6 characters."}
        elif "INVALID_EMAIL" in error_msg:
            return {"success": False, "user_id": None, "message": "Please enter a valid email address."}
        return {"success": False, "user_id": None, "message": f"Sign up failed: {error_msg}"}


def sign_in(email: str, password: str) -> Dict[str, Any]:
    """
    Sign in an existing user.

    Returns:
        Dict with 'success', 'user_id', 'message' keys
    """
    auth = get_auth()

    if not auth:
        return {"success": False, "user_id": None, "message": "Firebase not configured"}

    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return {
            "success": True,
            "user_id": user['localId'],
            "id_token": user['idToken'],
            "message": "Signed in successfully!"
        }
    except Exception as e:
        error_msg = str(e)
        if "INVALID_PASSWORD" in error_msg or "INVALID_LOGIN_CREDENTIALS" in error_msg:
            return {"success": False, "user_id": None, "message": "Incorrect email or password."}
        elif "EMAIL_NOT_FOUND" in error_msg:
            return {"success": False, "user_id": None, "message": "No account found with this email."}
        return {"success": False, "user_id": None, "message": f"Sign in failed: {error_msg}"}


def get_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Fetch user profile data from database."""
    db = get_db()
    if not db:
        return None

    try:
        data = db.child("users").child(user_id).get()
        return data.val()
    except Exception as e:
        print(f"Error fetching user data: {e}")
        return None


def update_currency(user_id: str, amount: int) -> bool:
    """Add fish to user's balance."""
    db = get_db()
    if not db:
        return False

    try:
        # Get current currency
        current_data = get_user_data(user_id)
        if current_data is None:
            return False

        current_currency = current_data.get("currency", 0)
        new_currency = current_currency + amount

        db.child("users").child(user_id).update({"currency": new_currency})
        return True
    except Exception as e:
        print(f"Error updating currency: {e}")
        return False


def increment_solved_questions(user_id: str) -> bool:
    """Increment the count of solved questions."""
    db = get_db()
    if not db:
        return False

    try:
        current_data = get_user_data(user_id)
        if current_data is None:
            return False

        current_count = current_data.get("solved_questions", 0)
        db.child("users").child(user_id).update({"solved_questions": current_count + 1})
        return True
    except Exception as e:
        print(f"Error incrementing solved questions: {e}")
        return False


def purchase_item(user_id: str, item_id: str, price: int) -> Dict[str, Any]:
    """
    Purchase an accessory from the shop.

    Returns:
        Dict with 'success' and 'message' keys
    """
    db = get_db()
    if not db:
        return {"success": False, "message": "Database not available"}

    try:
        user_data = get_user_data(user_id)
        if user_data is None:
            return {"success": False, "message": "User not found"}

        current_currency = user_data.get("currency", 0)
        inventory = user_data.get("inventory", [])

        # Check if already owned
        if item_id in inventory:
            return {"success": False, "message": "You already own this item!"}

        # Check if enough currency
        if current_currency < price:
            return {"success": False, "message": f"Not enough fish! You need {price - current_currency} more."}

        # Purchase the item
        new_currency = current_currency - price
        inventory.append(item_id)

        db.child("users").child(user_id).update({
            "currency": new_currency,
            "inventory": inventory
        })

        return {"success": True, "message": "Item purchased!"}
    except Exception as e:
        return {"success": False, "message": f"Purchase failed: {e}"}


def equip_item(user_id: str, item_id: str, slot: str) -> bool:
    """Equip an accessory to the owl."""
    db = get_db()
    if not db:
        return False

    try:
        user_data = get_user_data(user_id)
        if user_data is None:
            return False

        # Check if user owns the item
        inventory = user_data.get("inventory", [])
        if item_id not in inventory:
            return False

        # Update equipped slot
        equipped = user_data.get("equipped", {})
        equipped[slot] = item_id

        db.child("users").child(user_id).update({"equipped": equipped})
        return True
    except Exception as e:
        print(f"Error equipping item: {e}")
        return False


def unequip_item(user_id: str, slot: str) -> bool:
    """Remove an accessory from the owl."""
    db = get_db()
    if not db:
        return False

    try:
        user_data = get_user_data(user_id)
        if user_data is None:
            return False

        equipped = user_data.get("equipped", {})
        equipped[slot] = None

        db.child("users").child(user_id).update({"equipped": equipped})
        return True
    except Exception as e:
        print(f"Error unequipping item: {e}")
        return False
