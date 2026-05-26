import json
from typing import List
from pathlib import Path

from config import Settings

class MealPlannerService:
    def __init__(self):
        self.weekly_meals = self._load_weekly_meals_from_file()

    def _load_weekly_meals_from_file(self):
        settings = Settings()
        # Ensure PROJECT_ROOT always has a valid value
        PROJECT_ROOT = Path(settings.PROJECT_ROOT) if settings.PROJECT_ROOT else Path.cwd()
        CONFIG_DIR = PROJECT_ROOT / "config"
        MEAL_PLANNER_FILE = CONFIG_DIR / "meal_planner_data.json"

        with open(MEAL_PLANNER_FILE, 'r') as f:
            data = json.load(f)
        return data

    def get_weekly_meals(self) -> List[dict]:
        """
        Returns a list of meals for each day of the week.

        Returns:
            List[dict]: A list of meals for each day of the week.
        """
        return self.weekly_meals