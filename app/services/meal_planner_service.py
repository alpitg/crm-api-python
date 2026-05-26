import json
import random
import uuid
from typing import List
from pathlib import Path

from app.services.meal_generator_service import generate_meal_plan
from config import Settings


class MealPlannerService:
    def __init__(self):
        settings = Settings()

        # Ensure PROJECT_ROOT always has a valid value
        PROJECT_ROOT = (
            Path(settings.PROJECT_ROOT)
            if settings.PROJECT_ROOT
            else Path.cwd()
        )

        CONFIG_DIR = PROJECT_ROOT / "config"

        self.MEAL_PLANNER_FILE = (
            CONFIG_DIR / "meal_planner_data.json"
        )

        self.weekly_meals = self._load_weekly_meals_from_file()

    def _load_weekly_meals_from_file(self):
        with open(self.MEAL_PLANNER_FILE, "r") as f:
            data = json.load(f)

        return data

    def _save_weekly_meals_to_file(self):
        with open(self.MEAL_PLANNER_FILE, "w") as f:
            json.dump(
                self.weekly_meals,
                f,
                indent=4,
            )

    def get_weekly_meals(self) -> List[dict]:
        """
        Returns a list of meals for each day of the week.
        """
        return self.weekly_meals

    def generate_meal(self):
        """
        Returns a suggested meal.
        """
        # return self.weekly_meals[0].get("meals")[0]
        defaultMealRequestPayload = {
            "vegNonVeg": "veg",
            "region": "Indian",
            "highProtein": False,
            "quickCooking": False,
            "maidModeEnabled": False,
            "maidVoiceLanguage": "english",
            "maidLessSpicy": False,
            "maidEasyCook": False,
            "planOption": "today",
        };
        result = generate_meal_plan(defaultMealRequestPayload)
        return random.choice(result) if result else None
    

    def add_meal(
        self,
        day: str,
        meal_data,
    ):
        """
        Add new meal to a specific day.
        """

        meal_dict = (
            meal_data.dict()
            if hasattr(meal_data, "dict")
            else dict(meal_data)
        )

        # Generate unique ID
        meal_dict["id"] = str(uuid.uuid4())

        for day_item in self.weekly_meals:
            if day_item["day"].lower() == day.lower():

                if "meals" not in day_item:
                    day_item["meals"] = []

                day_item["meals"].append(meal_dict)

                self._save_weekly_meals_to_file()

                return meal_dict

        raise ValueError(f"Day '{day}' not found")

    def update_meal(
        self,
        meal_id: str,
        meal_data,
    ):
        """
        Update meal by ID.
        """

        updated_meal = (
            meal_data.dict()
            if hasattr(meal_data, "dict")
            else dict(meal_data)
        )

        updated_meal["id"] = meal_id

        for day_item in self.weekly_meals:

            meals = day_item.get("meals", [])

            for index, meal in enumerate(meals):

                if str(meal.get("id")) == str(meal_id):

                    meals[index] = updated_meal

                    self._save_weekly_meals_to_file()

                    return updated_meal

        raise ValueError(f"Meal with ID '{meal_id}' not found")

    def delete_meal(
        self,
        day: str,
        meal_id: str,
    ):
        """
        Delete meal by day and ID.
        """

        for day_item in self.weekly_meals:

            if day_item["day"].lower() == day.lower():

                meals = day_item.get("meals", [])

                filtered_meals = [
                    meal
                    for meal in meals
                    if str(meal.get("id")) != str(meal_id)
                ]

                if len(filtered_meals) == len(meals):
                    raise ValueError(
                        f"Meal with ID '{meal_id}' not found"
                    )

                day_item["meals"] = filtered_meals

                self._save_weekly_meals_to_file()

                return {
                    "success": True,
                    "message": "Meal deleted successfully",
                }

        raise ValueError(f"Day '{day}' not found")