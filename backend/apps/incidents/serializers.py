from rest_framework import serializers
from apps.accounts.serializers import UserSerializer
from apps.action_plans.serializers import ActionPlanSerializer
from .models import Incident, IncidentStatusHistory, IncidentComment
from .sla import compute_sla


class IncidentStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = UserSerializer(read_only=True)
    previous_status_display = serializers.SerializerMethodField()
    new_status_display = serializers.SerializerMethodField()

    class Meta:
        model = IncidentStatusHistory
        fields = ['id', 'previous_status', 'previous_status_display',
                  'new_status', 'new_status_display', 'changed_by', 'changed_at', 'comment']

    def get_previous_status_display(self, obj):
        return dict(Incident.STATUS_CHOICES).get(obj.previous_status, '')

    def get_new_status_display(self, obj):
        return dict(Incident.STATUS_CHOICES).get(obj.new_status, '')


class IncidentCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = IncidentComment
        fields = ['id', 'author', 'content', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']


class IncidentListSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    criticality_display = serializers.CharField(source='get_criticality_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    incident_type_display = serializers.CharField(source='get_incident_type_display', read_only=True)

    class Meta:
        model = Incident
        fields = [
            'id', 'title', 'incident_type', 'incident_type_display',
            'criticality', 'criticality_display', 'status', 'status_display',
            'affected_area', 'detected_at', 'deadline',
            'created_by', 'assigned_to', 'created_at',
        ]


class IncidentDetailSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    criticality_display = serializers.CharField(source='get_criticality_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    incident_type_display = serializers.CharField(source='get_incident_type_display', read_only=True)
    status_history = IncidentStatusHistorySerializer(many=True, read_only=True)
    comments = IncidentCommentSerializer(many=True, read_only=True)
    action_plan = ActionPlanSerializer(read_only=True)
    sla = serializers.SerializerMethodField()

    class Meta:
        model = Incident
        fields = '__all__'

    def get_sla(self, obj):
        return compute_sla(obj)


class IncidentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            'title', 'description', 'incident_type', 'criticality',
            'affected_area', 'affected_system', 'detected_at', 'deadline',
            'assigned_to',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        incident = Incident.objects.create(created_by=user, **validated_data)
        # Registro inicial en historial
        IncidentStatusHistory.objects.create(
            incident=incident,
            previous_status='',
            new_status=Incident.ABIERTO,
            changed_by=user,
            comment='Incidente registrado.'
        )
        return incident


class IncidentUpdateSerializer(serializers.ModelSerializer):
    new_status = serializers.ChoiceField(choices=Incident.STATUS_CHOICES, required=False, write_only=True)
    status_comment = serializers.CharField(required=False, write_only=True, allow_blank=True)

    class Meta:
        model = Incident
        fields = [
            'title', 'description', 'incident_type', 'criticality',
            'affected_area', 'affected_system', 'detected_at', 'deadline',
            'assigned_to', 'new_status', 'status_comment',
        ]

    def validate(self, attrs):
        incident = self.instance
        if incident and incident.is_closed:
            raise serializers.ValidationError("Un incidente cerrado no puede modificarse.")

        # ── Workflow por rol (V1.1) ──────────────────────────────────────
        role = self.context['request'].user.role
        new_status = attrs.get('new_status')

        # Jefe de Área: su único poder es VALIDAR el cierre. Nada de editar.
        if role == 'jefe_area':
            otros = [k for k in attrs if k not in ('new_status', 'status_comment')]
            if otros or new_status != Incident.CERRADO:
                raise serializers.ValidationError(
                    "El Jefe de Área solo puede validar el cierre de un incidente resuelto."
                )

        # Cerrar = validar: solo Jefe de Área o Admin TI, y solo desde 'resuelto'.
        if new_status == Incident.CERRADO:
            if role not in ('jefe_area', 'admin_ti'):
                raise serializers.ValidationError(
                    "Solo el Jefe de Área o el Administrador TI pueden cerrar (validar) un incidente."
                )
            if incident and incident.status != Incident.RESUELTO:
                raise serializers.ValidationError(
                    "Solo se puede cerrar un incidente que esté en estado Resuelto."
                )
        return attrs

    def update(self, instance, validated_data):
        new_status = validated_data.pop('new_status', None)
        status_comment = validated_data.pop('status_comment', '')
        user = self.context['request'].user

        if new_status and new_status != instance.status:
            IncidentStatusHistory.objects.create(
                incident=instance,
                previous_status=instance.status,
                new_status=new_status,
                changed_by=user,
                comment=status_comment
            )
            instance.status = new_status

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
