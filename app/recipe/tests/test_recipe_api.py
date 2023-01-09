from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import (Recipe, Tag, Ingredient)

from recipe.serializers import (
    RecipeSerializer,
    RecipeDetailSerializer,
    )

RECIPES_URL = reverse("recipe:recipe-list")

def detail_url(recipe_id):
    """ create and returns recipe detail URL"""
    return reverse("recipe:recipe-detail", args=[recipe_id])

def create_recipe(user, **params):
    defaults = {
        'title': 'Sample recipe title',
        "time_minutes": 22,
        "price": Decimal('5.25'),
        'description': 'Sample recipe description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe

def create_user(**params):
    """ create and return a new user """
    return get_user_model().objects.create_user(**params)

class PublicRecipeAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        res=self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateRecipeAPITests(TestCase):
    """ test authenticate API requests"""

    def setUp(self):
        self.client=APIClient()
        self.user = create_user(email='user@example.com',password='test123')
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res=self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        other_user= create_user(
            email="other@example.com",
            password="pass123word",
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res= self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer= RecipeSerializer(recipes, many= True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """ test get recipe detail """
        recipe = create_recipe(user=self.user)
        url=detail_url(recipe.id)
        res= self.client.get(url)
        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """ test create recipe """
        payload = {
            'title': 'Sample recipe title',
            "time_minutes": 22,
            "price": Decimal('5.25'),
        }
        res= self.client.post(RECIPES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipe = Recipe.objects.get(id=res.data['id'])
        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        """ test partial update of a recipe"""
        original_link='https://example.com/recipe.pdf'
        recipe = create_recipe (
            user=self.user,
            title="sample recipe title",
            link=original_link,
        )
        payload = {'title' : "new recipe title"}
        url=detail_url(recipe.id)
        res= self.client.patch(url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        """ test full update of a recipe"""

        recipe = create_recipe (
            user=self.user,
            title="sample recipe title",
            link= 'https://example.com/recipe.pdf',
            description="sample recipe description",
        )
        payload = {
            'title' : "new recipe title",
            'link' : 'https://example.com/recipe.pdf',
            'description' : "New sample recipe description",
            'time_minutes' : 22,
            'price' : Decimal('5.25'),
        }
        url = detail_url(recipe.id)
        res= self.client.patch(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        recipe.refresh_from_db()
        for k,v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_upate_returns_error(self):
        """ test changing the recipe user results in an error"""

        new_user = create_user(email='user2@example.com',
        password='test123')
        recipe = create_recipe(user=new_user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url,payload)
        recipe.refresh_from_db()
        self.assertEqual(recipe.user, new_user)

    def test_delete_recipe(self):
        """ test deleting a recipe"""

        recipe = create_recipe(user=self.user)
        url=detail_url(recipe.id)
        res= self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_delete_recipe_not_found(self):
        """ test deleting a recipe that does not exist"""
        new_user= create_user(email="user2@example.com",
        password="test123")
        recipe = create_recipe(user=new_user)
        url=detail_url(recipe.id)
        res= self.client.delete(url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {'title': 'poulet au curry',
                    'time_minutes': 30,
                    'price': Decimal('1.30'),
                    'tags': [{'name' : 'Thai'}, {'name' : 'Diner'}]
        }
        res=self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag_indien = Tag.objects.create(user=self.user, name="Indien")
        payload = {
            "title": "Massa",
            'time_minutes':60,
            'price': Decimal("4.40"),
            'tags': [{'name': "Indien"}, {"name": "Petit dej"}]
        }
        res= self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)
        recipe = recipes[0]
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag_indien, recipe.tags.all())
        for tag in payload["tags"]:
            exists = recipe.tags.filter(
                name=tag["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        """ test creating tag when updating a recipe """
        recipe = create_recipe(user=self.user)
        payload = {
            "tags": [{"name": "petit dej"}]
        }
        url = detail_url(recipe.id)
        res= self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        new_tag = Tag.objects.get(user=self.user, name='petit dej')
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        """ test assigning an existing tag when updating a recipe  """
        tag_breakfast = Tag.objects.create(user=self.user, name='Breakfast')
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag_breakfast)

        tag_lunch = Tag.objects.create(user=self.user, name='lunch')
        payload = {'tags': [{'name':'lunch'}]}
        url = detail_url(recipe.id)
        res= self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, 200)
        self.assertIn(tag_lunch, recipe.tags.all())
        self.assertNotIn(tag_breakfast, recipe.tags.all())

    def test_clear_recipe_tags(self):
        """ test clearing a recipes tag"""
        tag = Tag.objects.create(user=self.user, name="dessert")
        recipe = create_recipe(user=self.user)
        recipe.tags.add(tag)

        payload = {'tags': []}
        url=detail_url(recipe.id)
        res=self.client.patch(url,payload, format='json')

        self.assertEqual(res.status_code, 200)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredient(self):
        payload = {
            'title': 'Tacos',
            'time_minutes':60,
            'price' : Decimal('4.30'),
            'ingredients' : [{'name':'truc à tacos'}, {'name': 'sel'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, 201) #created
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(),2)
        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient["name"],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_creating_recipe_with_existing_ingredient(self):
        ingredient = Ingredient.objects.create(user=self.user, name="citron")
        payload = {
            "title": "Soupe Thai",
            "time_minutes" : 25,
            "price" : Decimal("2.56"),
            'ingredients': [{"name": "citron"}, {"name": "Soupe de poisson"}],
        }
        res = self.client.post(RECIPES_URL, payload, format= "json")

        self.assertEqual(res.status_code, 201)
        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(),1)
        recipe=recipes[0]
        self.assertEqual(recipe.ingredients.count(),2)
        self.assertIn(ingredient,recipe.ingredients.all())
        for ingredient in payload['ingredients']:
            exists= recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        """ test creating an ingredient when updating a recipe"""
        recipe = create_recipe(self.user)
        payload = {'ingredients': [{'name':'truffe blanche'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEqual(res.status_code, 200)
        new_ingredient = Ingredient.objects.get(user=self.user, name="truffe blanche")
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        """ test assigning an existing ingredient when updating a recipe"""
        ingredient1 = Ingredient.objects.create(user=self.user, name="Poivre")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient1)

        ingredient2 = Ingredient.objects.create(user=self.user, name="Poivre de Cayenne")
        payload = {"ingredients" : [{'name' : "Poivre de Cayenne"  }]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format="json")

        self.assertEquals(res.status_code,200)
        self.assertIn(ingredient2, recipe.ingredients.all())
        self.assertNotIn(ingredient1, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        ingredient=Ingredient.objects.create(user=self.user, name="Ail")
        recipe = create_recipe(user=self.user)
        recipe.ingredients.add(ingredient)

        payload = {"ingredients" : []}
        url = detail_url(recipe.id)
        res= self.client.patch(url, payload, format="json")
        self.assertEquals(res.status_code,200)
        self.assertEqual(recipe.ingredients.count(),0)


