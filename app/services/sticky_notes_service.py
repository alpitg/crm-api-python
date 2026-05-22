def get_sticky_notes_list():
    return [
        {
            "id": 1,
            "title": "1 Cup Black coffee (no sugar)",
            "description": "",
            "isPinned": False,
        },
        {
            "id": 2,
            "title": "Ginger + Cinnamon tea",
            "description": "",
            "isPinned": True,
        },
        {
            "id": 3,
            "title": "Cinnamon tea",
            "description": "",
            "isPinned": False,
        }
    ]

# app/services/sticky_notes_service.py

def create_sticky_note(payload):
    # Replace with DB logic
    new_note = {
        "id": 123,  # generate from DB
        "title": payload.title,
        "description": payload.description,
        "isPinned": False,
    }

    return new_note