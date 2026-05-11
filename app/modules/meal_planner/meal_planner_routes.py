
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
            "name": "Paneer Butter Masala",
            "type": "Veg",
            "servings": 4,
            "cookingTime": 30,
            "ingredients": [
                "Paneer",
                "Tomato",
                "Butter",
                "Cream",
            ],
            "recipe": [
                "Heat butter in pan",
                "Cook tomatoes",
                "Add paneer",
                "Serve hot",
            ],
        },
        {
            "name": "Jeera Rice",
            "type": "Veg",
            "servings": 4,
            "cookingTime": 20,
            "ingredients": [
                "Rice",
                "Jeera",
                "Ghee",
            ],
            "recipe": [
                "Boil rice",
                "Temper jeera in ghee",
                "Mix together",
            ],
        },
    ]

    return response