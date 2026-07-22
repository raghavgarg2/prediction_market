from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import RegisterSerializer,LoginSerializer
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken




class RegisterAPIView(APIView):

    def post(self,request):
        serializer = RegisterSerializer(
            data = request.data
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({
            "msg" : "User created successfully",
            "user" : serializer.data
        },status = status.HTTP_201_CREATED)


# class LoginAPIView(APIView):

#     def post(self,request):

#         serializer = LoginSerializer(
#             data = request.data
#         )

#         serializer.is_valid(raise_exception=True)

#         user = authenticate(
#             username = serializer.validated_data["username"],
#             password = serializer.validated_data["password"]
#         )

#         if user is None:
#             return Response({
#                 "msg" : "invalid credentials"
#             },status=status.HTTP_401_UNAUTHORIZED)
        
#         refresh = RefreshToken.for_user(user)
#         refresh_token = str(refresh)
#         access_token = str(refresh.access_token)

#         return Response(
#         {
#         "msg" : "user signed in successfully",
#         "access": access_token,
#         "refresh": refresh_token
#         },
#         status=status.HTTP_200_OK
#         )

        
class LoginAPIView(APIView):

    def post(self,request):
        serializer = LoginSerializer(
            data = request.data
            )
        
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            **serializer.validated_data
        )

        if user is None:
            return Response({
                "msg" : "invalid credentials"
            },status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)

        refresh_token = str(refresh)
        access_token = str(refresh.access_token)

        return Response({
            "msg" : "logged in successfully",
            "refreshToken" : refresh_token,
            "accessToken" : access_token
        },
        status=status.HTTP_200_OK)



