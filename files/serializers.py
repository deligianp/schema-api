from rest_framework import serializers


class UploadInputSerializer(serializers.Serializer):
    size = serializers.IntegerField()
    file_path = serializers.CharField()
