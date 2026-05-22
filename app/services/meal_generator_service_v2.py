import os
import json
import logging
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, ValidationError

# --------------------------------------------------
# Load Environment Variables
# --------------------------------------------------

load_dotenv()

# --------------------------------------------------
# Logging Configuration
# --------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger(__name__)

# --------------------------------------------------
# OpenAI Client
# --------------------------------------------------

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# --------------------------------------------------
# Pydantic Models
# --------------------------------------------------


class Meal(BaseModel):
    name: str
    type: str
    servings: int
    cookingTime: int
    ingredients: List[str]
    recipe: List[str]


class MealPlanRequest(BaseModel):
    planOption: str
    vegNonVeg: str
    region: str
    highProtein: bool
    quickCooking: bool
    maidModeEnabled: bool
    maidVoiceLanguage: str
    maidLessSpicy: bool
    maidEasyCook: bool


# --------------------------------------------------
# System Prompt
# --------------------------------------------------

SYSTEM_PROMPT = """
You are an expert Indian meal planner AI.

Your task:
- Generate realistic Indian meals.
- Return ONLY valid JSON.
- No markdown.
- No explanation text.
- No additional commentary.

Requirements:
1. Generate Breakfast, Lunch, and Dinner.
2. Respect region preference.
3. Respect veg/non-veg preference.
4. Use common Indian household ingredients.
5. Recipes should be practical and realistic.
6. Recipes should contain clear numbered steps.
7. Cooking time should be in minutes.
8. Servings should be realistic.
9. Avoid duplicate meals.

Special Rules:
- If highProtein=true:
  Include paneer, dal, soy, sprouts, curd, eggs, chicken, etc.

- If quickCooking=true:
  Prefer meals under 20 minutes.

- If maidLessSpicy=true:
  Reduce spice levels.

- If maidEasyCook=true:
  Use beginner-friendly recipes.

Response Format:
[
  {
    "name": "Meal Name",
    "type": "Breakfast",
    "servings": 2,
    "cookingTime": 25,
    "ingredients": ["ingredient1", "ingredient2"],
    "recipe": [
      "1. Step one",
      "2. Step two"
    ]
  }
]
"""

# --------------------------------------------------
# Utility Functions
# --------------------------------------------------


def build_user_prompt(payload: MealPlanRequest) -> str:
    """
    Converts request payload into a clean prompt.
    """

    return f"""
Generate meal plan for the following preferences:

Plan Option: {payload.planOption}
Diet Type: {payload.vegNonVeg}
Region: {payload.region}
High Protein: {payload.highProtein}
Quick Cooking: {payload.quickCooking}
Maid Mode Enabled: {payload.maidModeEnabled}
Maid Voice Language: {payload.maidVoiceLanguage}
Less Spicy: {payload.maidLessSpicy}
Easy Cooking: {payload.maidEasyCook}

Return only JSON array.
"""


def validate_meal_plan(data: list) -> List[Meal]:
    """
    Validate AI response using Pydantic.
    """

    meals = []

    for item in data:
        meal = Meal(**item)
        meals.append(meal)

    return meals


# --------------------------------------------------
# Main Generator Function
# --------------------------------------------------


def generate_meal_plan(
    request_data: dict,
    model: str = "gpt-4.1-mini",
    temperature: float = 0.7,
    max_retries: int = 3
) -> List[dict]:
    """
    Generate meal plan using OpenAI API.
    """

    try:
        payload = MealPlanRequest(**request_data)

    except ValidationError as e:
        logger.error("Invalid request payload")
        raise ValueError(e.errors())

    user_prompt = build_user_prompt(payload)

    logger.info("Generating AI meal plan")

    for attempt in range(max_retries):

        try:

            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                response_format={
                    "type": "json_object"
                }
            )

            content = response.choices[0].message.content

            if not content:
                raise ValueError("Empty response from OpenAI")

            parsed_response = json.loads(content)

            # --------------------------------------------------
            # Handle wrapped JSON object
            # --------------------------------------------------

            if isinstance(parsed_response, dict):

                # Support:
                # {"meals": [...]}

                if "meals" in parsed_response:
                    parsed_response = parsed_response["meals"]

                # Support:
                # {"data": [...]}

                elif "data" in parsed_response:
                    parsed_response = parsed_response["data"]

                else:
                    raise ValueError(
                        "Unexpected JSON structure received from AI"
                    )

            # --------------------------------------------------
            # Validate Response
            # --------------------------------------------------

            validated_meals = validate_meal_plan(parsed_response)

            logger.info("Meal plan generated successfully")

            return [meal.model_dump() for meal in validated_meals]

        except (
            json.JSONDecodeError,
            ValidationError,
            ValueError
        ) as e:

            logger.warning(
                f"Attempt {attempt + 1} failed: {str(e)}"
            )

            if attempt == max_retries - 1:
                logger.error("Max retries exceeded")
                raise Exception(
                    "Failed to generate valid meal plan"
                )

        except Exception as e:

            logger.exception("Unexpected error occurred")

            raise Exception(
                f"Meal generation failed: {str(e)}"
            )

    return []


# --------------------------------------------------
# Example Usage
# --------------------------------------------------

if __name__ == "__main__":

    sample_request = {
        "planOption": "today",
        "vegNonVeg": "veg",
        "region": "north",
        "highProtein": False,
        "quickCooking": False,
        "maidModeEnabled": False,
        "maidVoiceLanguage": "none",
        "maidLessSpicy": False,
        "maidEasyCook": False
    }

    result = generate_meal_plan(sample_request)

    print(json.dumps(result, indent=2))