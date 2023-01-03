from django.shortcuts import render

from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from core.models import Recipe
from recipe import serializers

class RecipeViewSet(viewsets.ModelViewSet):
    """view for manage recipe APIs"""
    serializer_class = serializers.RecipeDetailSerializer
    queryset = Recipe.objects.all()
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """ retrieve recipe for authenticated user"""
        return self.queryset.filter(user=self.request.user).order_by('-id')

    def get_serializer_class(self):
        """ return the serializer class for the request"""
        if self.action == 'list':
            return serializers.RecipeSerializer
        return self.serializer_class

    def perform_create(self, serializer):
        """ create a new recipe"""
        serializer.save(user=self.request.user)
        