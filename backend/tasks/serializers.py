from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        # fields = ['id', 'title', 'due_date', 'estimated_hours', 'importance', 'dependencies']
        fields = '__all__'  # or list specific fields
