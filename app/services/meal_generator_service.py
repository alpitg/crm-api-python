import json
from typing import List
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
import os
import logging

from app.modules.meal_planner.schemas.meal_planner import MealOut, MealRequestIn

from app.modules.meal_planner.schemas.meal_planner import MealOut
from app.utils.json_util import to_json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are an Indian meal planning assistant.

Return STRICT JSON only.
No markdown. No explanations.

Generate:
- Breakfast
- Lunch
- Dinner

Rules:
- Respect region and dietary preferences.
- Use realistic Indian meals and household ingredients.
- Include ingredients and step-by-step instructions.
- If highProtein=true, prefer protein-rich meals.
- If quickCooking=true, prefer meals under 30 mins.
- If maidLessSpicy=true, keep spice mild.
- If maidEasyCook=true, use beginner-friendly recipes.
- If maidModeEnabled=true, include meals needing soaking/marination/prep in advance.

Prefer dishes like:
- Breakfast: poha, upma, chilla, idli, dosa, paratha, eggs
- Lunch/Dinner: dal, rice, roti, sabzi, khichdi, pulao, curry

JSON format:
[
  {
    "name": "Meal Name",
    "type": "Breakfast",
    "servings": 2,
    "cookingTime": 30,
    "ingredients": ["item1", "item2"],
    "recipe": ["Suggestion", "Step 1", "Step 2"]
  }
]
"""


FALLBACK_RESPONSE = [
    {
        "name": "Aloo Paratha",
        "type": "Breakfast",
        "servings": 2,
        "cookingTime": 30,
        "ingredients": ["Potato", "Onion"],
        "recipe": [
            "1. Boil and mash 2 potatoes, mix with finely chopped onion and salt",
            "2. Knead whole wheat flour with water to make dough",
            "3. Divide dough into balls and fill with potato mixture",
            "4. Roll into flat bread and cook on hot griddle until golden",
            "5. Serve with pickle or yogurt"
        ]
    },
    {
        "name": "Paneer Tomato Rice",
        "type": "Lunch",
        "servings": 2,
        "cookingTime": 35,
        "ingredients": ["Paneer", "Tomato", "Onion", "Rice"],
        "recipe": [
            "1. Cube paneer into small pieces",
            "2. Finely chop onions and tomatoes",
            "3. Heat oil, sauté onions until golden",
            "4. Add chopped tomatoes and cook until soft",
            "5. Add boiled rice, paneer cubes, and salt to taste",
            "6. Mix well and cook for 3-4 minutes",
            "7. Garnish with fresh cilantro and serve hot"
        ]
    },
    {
        "name": "Aloo Tomato Curry",
        "type": "Dinner",
        "servings": 2,
        "cookingTime": 25,
        "ingredients": ["Potato", "Tomato", "Onion"],
        "recipe": [
            "1. Cut potatoes into small cubes",
            "2. Chop onions and tomatoes finely",
            "3. Heat oil and sauté chopped onions until golden",
            "4. Add potato cubes and cook for 5 minutes",
            "5. Add tomatoes and salt, cook covered for 10 minutes",
            "6. Stir occasionally until potatoes are soft",
            "7. Serve hot as a side dish with rice or bread"
        ]
    }
]


def generate_meal_plan(user_input: MealRequestIn) -> List[MealOut]:

    try:

        user_prompt = f"""
        Generate meal plan:

        {to_json(user_input)}
        """

        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0.7,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ]
        )

        content = response.choices[0].message.content

        if not content:
            raise ValueError("Empty response from OpenAI")

        parsed = json.loads(content)

        # Handle wrapped response
        if isinstance(parsed, dict):

            if "meals" in parsed:
                parsed = parsed["meals"]

            elif "data" in parsed:
                parsed = parsed["data"]

        return [MealOut(**meal) for meal in parsed]

    except RateLimitError as e:

        logger.error(f"OpenAI quota/rate limit error: {str(e)}")

        return [MealOut(**meal) for meal in FALLBACK_RESPONSE]

    except json.JSONDecodeError as e:

        logger.error(f"Invalid JSON response: {str(e)}")

        return [MealOut(**meal) for meal in FALLBACK_RESPONSE]

    except Exception as e:

        logger.error(f"Meal generation failed: {str(e)}")

        return [MealOut(**meal) for meal in FALLBACK_RESPONSE]