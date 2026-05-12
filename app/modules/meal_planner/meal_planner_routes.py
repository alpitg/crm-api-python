
from typing import List

from fastapi import APIRouter, Depends

from app.utils.auth_utils import authenticate
from app.modules.meal_planner.schemas.meal_planner import MealRequestIn, MealOut


router = APIRouter(
    # dependencies=[Depends(authenticate)],
)

@router.post(
    "/meal-request",
    response_model=List[MealOut],
)
async def create_meal_request(payload: MealRequestIn):
    """
    Create meal request and return meal plans.
    """

    response = [
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


    return response