
from typing import List

from fastapi import APIRouter, Depends

from app.services.meal_generator_service import generate_meal_plan
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

    result = generate_meal_plan(payload)

    return result
