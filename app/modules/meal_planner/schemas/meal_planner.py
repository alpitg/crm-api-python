# =========================================================
# Request Models
# =========================================================

from typing import List, Optional

from pydantic import BaseModel
from typing_extensions import Literal


PlanOption = Literal["today", "breakfast", "lunch", "dinner"]

VegNonVegOption = Literal["veg", "non-veg"]

VoiceLanguageOption = Literal["none", "hindi", "marathi"]


class MealRequestIn(BaseModel):
    vegNonVeg: VegNonVegOption
    region: str
    highProtein: bool
    quickCooking: bool
    maidModeEnabled: bool
    maidVoiceLanguage: VoiceLanguageOption
    maidLessSpicy: bool
    maidEasyCook: bool
    planOption: PlanOption | None = "today"


# =========================================================
# Response Models
# =========================================================

class YoutubeLinkOut(BaseModel):
    title: str
    url: str

class MealOut(BaseModel):
    name: str
    type: str
    servings: int
    cookingTime: int
    ingredients: List[str]
    recipe: Optional[List[str]] = None
    youtubeLink: Optional[List[YoutubeLinkOut]] = None

