
from typing import List

from fastapi import APIRouter, Depends

from app.modules.meal_planner.schemas.sticky_notes import StickyNoteOut
from app.services.meal_generator_service import generate_meal_plan
from app.services.sticky_notes_service import get_sticky_notes_list
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


@router.get(
    "/sticky-notes",
    response_model=List[StickyNoteOut],
)
async def get_sticky_notes():
    """
    Return sticky notes list.
    """

    result = get_sticky_notes_list()

    return result
