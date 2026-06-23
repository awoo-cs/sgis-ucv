from django.utils import timezone
from rest_framework import serializers
from .models import ActionPlan


class ActionPlanSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        model = ActionPlan
        fields = ['id', 'incident', 'steps', 'is_customized', 'progress', 'created_at', 'updated_at']
        read_only_fields = ['id', 'incident', 'created_at', 'updated_at']

    def get_progress(self, obj):
        steps = obj.steps or []
        done = sum(1 for s in steps if isinstance(s, dict) and s.get('done'))
        total = len(steps)
        return {'done': done, 'total': total, 'pct': round(100 * done / total) if total else 0}

    def validate_steps(self, value):
        """Normaliza cada paso a {text, done, evidence, done_by, done_at}.

        Acepta también list[str] por compatibilidad con planes viejos.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError('steps debe ser una lista.')
        norm = []
        for s in value:
            if isinstance(s, str):
                s = {'text': s}
            if not isinstance(s, dict) or not str(s.get('text', '')).strip():
                raise serializers.ValidationError('Cada paso necesita un texto.')
            norm.append({
                'text': str(s['text']).strip(),
                'done': bool(s.get('done', False)),
                'evidence': str(s.get('evidence', '') or ''),
                'done_by': s.get('done_by'),
                'done_at': s.get('done_at'),
            })
        return norm

    def update(self, instance, validated_data):
        new_steps = validated_data.get('steps')
        if new_steps is not None:
            user = self.context['request'].user
            who = user.get_full_name() or user.username
            now = timezone.now().isoformat()
            old = instance.steps or []
            for i, s in enumerate(new_steps):
                prev = old[i] if i < len(old) and isinstance(old[i], dict) else {}
                if s['done'] and not prev.get('done'):
                    s['done_by'], s['done_at'] = who, now            # recién marcado
                elif s['done']:
                    s['done_by'] = prev.get('done_by') or who         # ya estaba marcado
                    s['done_at'] = prev.get('done_at') or now
                else:
                    s['done_by'] = s['done_at'] = None                # desmarcado
            old_texts = [(o.get('text') if isinstance(o, dict) else o) for o in old]
            if [s['text'] for s in new_steps] != old_texts:
                instance.is_customized = True                         # cambió el contenido
            instance.steps = new_steps
        instance.save()
        return instance
