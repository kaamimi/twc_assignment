from rest_framework import serializers
from .models import Organization, AdminUser


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'organization_name', 'collection_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'collection_name', 'created_at', 'updated_at']


class CreateOrganizationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    
    def validate_organization_name(self, value):
        """Check if organization name already exists"""
        if Organization.objects.filter(organization_name=value).exists():
            raise serializers.ValidationError("Organization with this name already exists.")
        return value
    
    def validate_email(self, value):
        """Check if email already exists"""
        if AdminUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Admin user with this email already exists.")
        return value


class UpdateOrganizationSerializer(serializers.Serializer):
    organization_name = serializers.CharField(max_length=255)
    new_organization_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=6)


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)