# CottonOGD/serializers.py
from rest_framework import serializers
from CottonOGD.server.base3D import SearchMethod

class SearchRequestSerializer(serializers.Serializer):
    sequence = serializers.CharField(min_length=5, help_text="蛋白序列")
    method = serializers.ChoiceField(
        choices=SearchMethod.choices(), 
        default=SearchMethod.RCSB_API,
        help_text="比对方法"
    )
    top_n = serializers.IntegerField(default=10, min_value=1, max_value=100)
    evalue = serializers.FloatField(default=0.001, min_value=0)
    identity_cutoff = serializers.FloatField(default=0.0, min_value=0, max_value=1)
    use_cache = serializers.BooleanField(default=True)

class MethodListSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    is_local = serializers.BooleanField()
