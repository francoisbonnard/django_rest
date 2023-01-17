""" Tests for the tags API """

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase

from decimal import Decimal

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Tag, Recipe
from recipe.serializers import TagsSerializer

TAGS_URL = reverse("recipe:tag-list")

def detail_url(tag_id):
    """ return a tag detail url """
    return reverse("recipe:tag-detail", args=[tag_id])

def create_user(email='user@example.com', password='testPass123'):
    return get_user_model().objects.create_user(email, password)

class PublicTagsApiTests(TestCase):
    """ test unauthenticated API requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """ test auth is required for retrieving tags"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

class PrivateTagsApiTests(TestCase):
    """ test auth API request """

    def setUp(self):
        self.user= create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_retrieve_tags(self):
        """ retrieving a list of tags"""
        Tag.objects.create(user=self.user, name="Vegan")
        Tag.objects.create(user=self.user, name="Desert")

        res= self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by("-name")
        serializer=TagsSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_to_user(self):
        """ list of tags is limited to auth user"""
        user2=create_user(email='user2@example.com')
        Tag.objects.create(user=user2, name="Fruity")
        tag=Tag.objects.create(user=self.user, name="Cool Food")

        res= self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data),1)
        self.assertEqual(res.data[0]['name'], tag.name)
        self.assertEqual(res.data[0]["id"],tag.id)

    def test_update_tag(self):
        """ upating a tag """
        tag = Tag.objects.create(user=self.user, name="apero")
        payload = {
            "name" : "dessert"
        }
        url = detail_url(tag.id)
        res=self.client.patch(url, payload)

        self.assertEqual(res.status_code, 200)
        tag.refresh_from_db()
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """ deleting a tag"""
        tag = Tag.objects.create(user=self.user,name="petit dej")
        url = detail_url(tag.id)
        res=self.client.delete(url)

        self.assertEqual(res.status_code,status.HTTP_204_NO_CONTENT) #no content
        tags=Tag.objects.filter(user=self.user)
        self.assertFalse(tags.exists())

    def test_filtered_tags_assigned_to_recipes(self):
        tag1 = Tag.objects.create(user=self.user,name="petit dej")
        tag2 = Tag.objects.create(user=self.user,name="midi")

        recipe = Recipe.objects.create(
            title="toast",
            time_minutes=4,
            price=Decimal("5.12"),
            user=self.user,
        )
        recipe.tags.add(tag1)
        res= self.client.get(TAGS_URL, {'assigned_only':1})

        s1=TagsSerializer(tag1)
        s2=TagsSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        tag = Tag.objects.create(user=self.user,name="petit dej")
        Tag.objects.create(user=self.user,name="diner")

        recipe1 = Recipe.objects.create(
            title="toast",
            time_minutes=4,
            price=Decimal("5.12"),
            user=self.user,
        )
        recipe2 = Recipe.objects.create(
            title="porridge",
            time_minutes=3,
            price=Decimal("3.12"),
            user=self.user,
        )

        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res= self.client.get(TAGS_URL, {"assigned_only":1})
