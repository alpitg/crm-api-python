
from typing import List

from fastapi import APIRouter, Depends

from app.modules.meal_planner.schemas.sticky_notes import StickyNoteIn, StickyNoteOut
from app.services.meal_generator_service import generate_meal_plan
from app.services.meal_planner_service import MealPlannerService
from app.services.sticky_notes_service import create_sticky_note, get_sticky_notes_list
from app.modules.meal_planner.schemas.meal_planner import MealPlanOut, MealRequestIn, MealOut


router = APIRouter(
    # dependencies=[Depends(authenticate)],
)

meal_planner_service = MealPlannerService()

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

@router.post(
    "/sticky-notes",
    response_model=StickyNoteOut,
)
async def create_sticky_notes(payload: StickyNoteIn):
    """
    Create a new sticky note.
    """

    result = create_sticky_note(payload)
    return result

@router.get("/weekly-meals", response_model=List[MealPlanOut])
async def get_weekly_meals():
    """
    Returns a list of meals for each day of the week.

    Returns:
        List[MealPlanOut]: A list of meal plans for each day of the week.
    """
    return meal_planner_service.get_weekly_meals()

# meals/generate endpoint should return only JSON array of meals, without any wrapping object. Each meal should have the following structure:

@router.post("/meals/generate", response_model=MealOut)
async def generate_meal():
    """
    Returns a suggested meal.

    Returns:
        MealOut: A suggested meal.
    """
    return meal_planner_service.generate_meal()