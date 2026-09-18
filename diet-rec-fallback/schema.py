from pydantic import BaseModel, Field

class MealItem(BaseModel):
    meal_type: str = Field(description="Type of meal (e.g., Breakfast, Lunch, Dinner, Snack).")
    recipe_name: str = Field(description="Name of the meal or recipe.")
    calories: int = Field(description="Estimated calories for this meal.")
    protein_g: int = Field(description="Total protein content in grams.")
    carbs_g: int = Field(description="Total carbohydrate content in grams.")
    fat_g: int = Field(description="Total fat content in grams.")
    ingredients: list[str] = Field(description="Raw ingredients needed.")
    prep_tip: str = Field(description="Quick preparation tip.")

class DietPlanResponse(BaseModel):
    conversational_intro: str = Field(description="Encouraging summary statement.")
    daily_total_calories: int = Field(description="Sum of all meals' calories.")
    total_protein_g: int = Field(description="Sum of protein grams.")
    total_carbs_g: int = Field(description="Sum of carbohydrate grams.")
    total_fat_g: int = Field(description="Sum of fat grams.")
    meals: list[MealItem] = Field(description="Set of exactly 3-4 meal recommendations.")
