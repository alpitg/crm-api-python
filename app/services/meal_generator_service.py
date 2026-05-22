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
You are an Indian nutrition meal planner.

Return STRICT JSON only. No text, no markdown, no extra keys.

Generate:
Breakfast, Lunch, Dinner

HARD RULE:
- MUST include at least 1 chilla per day (any meal)
- Allowed: moong dal, besan, oats, palak, paneer, sprouts chilla
- If missing → regenerate output

Rules:
1. Respect region + veg/non-veg preference
2. Use Indian household ingredients
3. Keep meals practical, healthy, realistic
4. No repeated meals/ingredients
5. Balanced protein + fiber + vegetables
6. Cooking time in minutes, servings realistic

YouTube:
- 1–3 items per meal, never empty
- Each item: title + url only

URL RULE (STRICT):
- ONLY use YouTube search URLs ex. https://www.youtube.com/results?search_query=KEYWORDS

Health focus:
chilla, paneer, dal, sprouts, vegetables, millet, oats, poha, upma, idli, dosa, khichdi, curd

High protein (if true):
paneer, dal, sprouts, eggs, chicken, soy, curd, besan

Quick cooking:
<30 min meals only

Maid mode:
less spicy + simple steps + prep tips

OUTPUT JSON:
[
  {
    "name": "string",
    "type": "Breakfast | Lunch | Dinner",
    "servings": number,
    "cookingTime": number,
    "ingredients": ["string"],
    "youtubeLink": [
        {
            "title": "Moong Dal Chilla Recipe | Healthy Breakfast",
            "url": "https://www.youtube.com/results?search_query=moong+dal+chilla+recipe"
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

            elif "mealPlan" in parsed:
                parsed = parsed["mealPlan"]

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