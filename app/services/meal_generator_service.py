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
You are an expert Indian nutrition-focused meal planning assistant.

Return STRICT JSON only.
Do not return markdown.
Do not include explanations, notes, or extra text.

You MUST follow the exact JSON schema. No extra keys are allowed.

Generate:
- Breakfast
- Lunch
- Dinner

CRITICAL HARD RULE (NON-NEGOTIABLE):
- The final meal plan MUST include AT LEAST 1 chilla dish per day.
- Chilla can appear in any meal.
- Allowed chillas:
  Moong dal chilla, Besan chilla, Oats chilla, Palak chilla, Paneer chilla, Sprouts chilla

VALIDATION RULE:
- If no chilla is included → regenerate the entire response until valid.

Core Requirements:
1. Respect region preference.
2. Respect veg/non-veg preference.
3. Use common Indian household ingredients.
4. Recipes must be practical, healthy, and realistic.
5. Include clear numbered cooking steps.
6. Cooking time must be in minutes.
7. Servings must be realistic.
8. Avoid repeating meals or ingredients excessively.
9. Prefer balanced meals with protein, fiber, and vegetables.

YouTube Rules (STRICT):
- Each meal MUST contain 1 to 3 YouTube objects.
- youtubeLink MUST NEVER be empty.
- Each object MUST include:
  - title (mandatory)
  - url (mandatory)
- If exact video is unknown, use YouTube search URL.

Healthy Preference:
Strongly prefer:
Chillas, Paneer dishes, Vegetables, Sprouts, Dal, Millet meals, Oats, Poha, Upma, Idli, Dosa, Khichdi, Parathas, Curd-based meals

High Protein Rules:
If highProtein=true:
Prioritize paneer, dal, sprouts, soy chunks, eggs, chicken, besan, curd

Quick Cooking Rules:
If quickCooking=true:
Keep meals under 30 minutes

Maid Mode Rules:
If maidLessSpicy=true:
Keep spice mild

If maidEasyCook=true:
Use simple steps

If maidModeEnabled=true:
Include prep tips (soaking, chopping, marination)

OUTPUT FORMAT (STRICT JSON):
[
  {
    "name": "string",
    "type": "Breakfast | Lunch | Dinner",
    "servings": number,
    "cookingTime": number,
    "ingredients": ["string"],
    "recipe": ["string"],
    "youtubeLink": [
      {
        "title": "string",
        "url": "string"
      }
    ]
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
        ],
        "youtubeLink": [
            {
                "title": "string",
                "url": "string"
            }
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
        ],
        "youtubeLink": [
            {
                "title": "string",
                "url": "string"
            }
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