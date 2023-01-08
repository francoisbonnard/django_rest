from rest_framework import serializers

from core.models import (Recipe, Tag, Ingredient)


class IngredientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Ingredient
        fields = ['id', 'name']
        read_only_fields = ['id']

class TagsSerializer(serializers.ModelSerializer):

    class Meta:
        model = Tag
        fields = ['id','name']
        read_only_fields = ['id']

class RecipeSerializer(serializers.ModelSerializer):
    """ Serializer for Recipe"""

    tags= TagsSerializer(many=True, required=False)
    # nested serializers

    class Meta:
        model = Recipe
        fields = ['id', 'title', 'time_minutes', 'price', 'link', 'tags']
        read_only_fields = ['id']

    def _get_or_create_tags(self,tags, recipe):
        """ Handle getting or creating tags as needed"""
        auth_user = self.context["request"].user #context is passed to the serializer by the view
        for tag in tags:
            tag_obj, created = Tag.objects.get_or_create(
                user=auth_user,
                **tag, # not name=tag["name"]
            )
            recipe.tags.add(tag_obj)

    def create(self, validated_data):
        """ overide recipe creation"""
        tags = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        self._get_or_create_tags(tags,recipe)
        return recipe

    def update(self, instance, validated_data):
        """ Update recipe"""
        tags = validated_data.pop("tags",None)
        if tags is not None:
            instance.tags.clear()
            self._get_or_create_tags(tags, instance)

        for attr,value in validated_data.items():
            setattr(instance,attr,value)

        instance.save()
        return instance



class RecipeDetailSerializer(RecipeSerializer):
    """ serializer for recipe detail view"""
    class Meta(RecipeSerializer.Meta):
        fields = RecipeSerializer.Meta.fields + ['description']
