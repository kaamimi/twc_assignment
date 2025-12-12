from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

from .models import Organization, AdminUser
from .serializers import (
    OrganizationSerializer,
    CreateOrganizationSerializer,
    UpdateOrganizationSerializer,
    AdminLoginSerializer
)
from .mongo_utils import MongoDBManager


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def create_organization(request):
    """Create a new organization with admin user"""
    serializer = CreateOrganizationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    organization_name = serializer.validated_data['organization_name']
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    mongo_manager = MongoDBManager()
    
    try:
        with transaction.atomic():
            # Create MongoDB collection
            collection_name = mongo_manager.create_organization_collection(organization_name)
            
            # Create organization in master database
            organization = Organization.objects.create(
                organization_name=organization_name,
                collection_name=collection_name
            )
            
            # Create admin user
            admin_user = AdminUser.objects.create(
                organization=organization,
                email=email
            )
            admin_user.set_password(password)
            admin_user.save()
            
            response_data = {
                'message': 'Organization created successfully',
                'organization': OrganizationSerializer(organization).data,
                'admin_email': email
            }
            
            return Response(response_data, status=status.HTTP_201_CREATED)
    
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Failed to create organization: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        mongo_manager.close()


@api_view(['GET'])
@permission_classes([AllowAny])
def get_organization(request):
    """Get organization details by name"""
    organization_name = request.query_params.get('organization_name')
    
    if not organization_name:
        return Response({'error': 'organization_name parameter is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        organization = Organization.objects.get(organization_name=organization_name)
        serializer = OrganizationSerializer(organization)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)


@csrf_exempt
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_organization(request):
    """Update organization details"""
    serializer = UpdateOrganizationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    organization_name = serializer.validated_data['organization_name']
    new_organization_name = serializer.validated_data.get('new_organization_name')
    email = serializer.validated_data.get('email')
    password = serializer.validated_data.get('password')
    
    try:
        organization = Organization.objects.get(organization_name=organization_name)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
    
    mongo_manager = MongoDBManager()
    
    try:
        with transaction.atomic():
            # Handle organization name change
            if new_organization_name and new_organization_name != organization_name:
                # Check if new name already exists
                if Organization.objects.filter(organization_name=new_organization_name).exists():
                    return Response({'error': 'New organization name already exists'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
                
                # Rename collection
                new_collection_name = mongo_manager.rename_organization_collection(
                    organization_name, new_organization_name
                )
                
                organization.organization_name = new_organization_name
                organization.collection_name = new_collection_name
            
            # Update admin user if email or password provided
            if email or password:
                admin_user = organization.admins.first()
                if email:
                    admin_user.email = email
                if password:
                    admin_user.set_password(password)
                admin_user.save()
            
            organization.save()
            
            return Response({
                'message': 'Organization updated successfully',
                'organization': OrganizationSerializer(organization).data
            }, status=status.HTTP_200_OK)
    
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Failed to update organization: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        mongo_manager.close()


@csrf_exempt
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_organization(request):
    """Delete organization and its collection"""
    organization_name = request.data.get('organization_name')
    
    if not organization_name:
        return Response({'error': 'organization_name is required'}, 
                       status=status.HTTP_400_BAD_REQUEST)
    
    try:
        organization = Organization.objects.get(organization_name=organization_name)
    except Organization.DoesNotExist:
        return Response({'error': 'Organization not found'}, status=status.HTTP_404_NOT_FOUND)
    
    mongo_manager = MongoDBManager()
    
    try:
        # Delete MongoDB collection
        mongo_manager.delete_organization_collection(organization_name)
        
        # Delete organization (cascades to admin users)
        organization.delete()
        
        return Response({'message': 'Organization deleted successfully'}, 
                       status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to delete organization: {str(e)}'}, 
                       status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    finally:
        mongo_manager.close()


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def admin_login(request):
    """Admin login endpoint"""
    serializer = AdminLoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    email = serializer.validated_data['email']
    password = serializer.validated_data['password']
    
    try:
        admin_user = AdminUser.objects.select_related('organization').get(email=email)
        
        if not admin_user.check_password(password):
            return Response({'error': 'Invalid credentials'}, 
                          status=status.HTTP_401_UNAUTHORIZED)
        
        # Generate JWT tokens
        refresh = RefreshToken()
        refresh['user_id'] = admin_user.id
        refresh['email'] = admin_user.email
        refresh['organization_id'] = admin_user.organization.id
        refresh['organization_name'] = admin_user.organization.organization_name
        
        return Response({
            'message': 'Login successful',
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'organization': {
                'id': admin_user.organization.id,
                'name': admin_user.organization.organization_name
            }
        }, status=status.HTTP_200_OK)
    
    except AdminUser.DoesNotExist:
        return Response({'error': 'Invalid credentials'}, 
                       status=status.HTTP_401_UNAUTHORIZED)
