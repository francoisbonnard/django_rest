from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Ingredient, Recipe
from recipe.serializers import IngredientSerializer

INGREDIENTS_URL = reverse("recipe:ingredient-list")

def create_user(email='user@example.com', password='testPass123'):
    """Create a new user"""
    return get_user_model().objects.create_user(email=email, password=password)

def detail_url(ingredient_id):
    """ create and return an ingredient detail URL"""
    return reverse("recipe:ingredient-detail", args=[ingredient_id])

class PublicIngredientsApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()

    def test_Auth_required(self):
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code,status.HTTP_401_UNAUTHORIZED)

class PrivateIngredientsApiTests(TestCase):
    """ test unauthenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_ingredients(self):
        """ retrieve a list of ingredients"""
        Ingredient.objects.create(user=self.user, name = "Choux")
        Ingredient.objects.create(user=self.user, name = "Vanille")

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_to_user(self):
        """ test list of ingredients limited to authenticated user """
        user2 = create_user(email="user2@example.com")
        Ingredient.objects.create(user=user2, name="Sel")
        ingredient = Ingredient.objects.create(user=self.user, name = "Poivre")

        res= self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code,200)
        self.assertEqual(len(res.data),1)
        self.assertEqual(res.data[0]['name'],ingredient.name)
        self.assertEqual(res.data[0]['id'],ingredient.id)

    def test_update_ingredient(self):
        """ test updating the ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name="farine")
        payload = {'name' : "farine de blé"}
        url = detail_url(ingredient.id)
        res = self.client.patch(url,payload)

        self.assertEqual(res.status_code,200)
        ingredient.refresh_from_db()
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """ test deleting the ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name="Salade")
        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code,status.HTTP_204_NO_CONTENT)
        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertFalse(ingredients.exists())


    def test_filter_ingredients_assigned_to_recipe(self):
        in1 = Ingredient.objects.create(user=self.user, name="Pomme")
        in2 = Ingredient.objects.create(user=self.user, name="Dinde")
        recipe = Recipe.objects.create(
            title="Crumble de Dinde",
            time_minutes=5,
            price=Decimal('4.50'),
            user = self.user,
        )
        recipe.ingredients.add(in1)

        res = self.client.get(INGREDIENTS_URL, {'assigned_only':1})

        s1 = IngredientSerializer(in1)
        s2 = IngredientSerializer(in2)

        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_ingredients_unique(self):
        """ test filtered ingredients returns a unique list"""
        ing = Ingredient.objects.create(user=self.user, name="Oeufs")
        Ingredient.objects.create(user=self.user, name="lentille")

        recipe1 = Recipe.objects.create(
            title="Oeufs coco",
            time_minutes=5,
            price=Decimal('4.50'),
            user = self.user,
        )
        recipe2 = Recipe.objects.create(
            title="Oeufs à la coque",
            time_minutes=4,
            price=Decimal('3.50'),
            user = self.user,
        )

        recipe1.ingredients.add(ing)
        recipe2.ingredients.add(ing)

        res=self.client.get(INGREDIENTS_URL, {"assigned_only": 1})

        self.assertEqual(len(res.data), 1)
