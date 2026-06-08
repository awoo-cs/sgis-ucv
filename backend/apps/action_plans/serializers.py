from rest_framework import serializers
from .models import ActionPlan


class ActionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionPlan
        fields = ['id', 'incident', 'steps', 'is_customized', 'created_at', 'updated_at']
        read_only_fields = ['id', 'incident', 'created_at', 'updated_at']

    def update(self, instance, validated_data):
        instance.steps = validated_data.get('steps', instance.steps)
        instance.is_customized = True
        instance.save()
        return instance
