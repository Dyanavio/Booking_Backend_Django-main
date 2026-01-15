from django.contrib import admin
from main.models import *

# Register your models here.

@admin.register(RealtyGroup)
class RealtyGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")

@admin.register(UserAccess)
class UserAccessAdmin(admin.ModelAdmin):
    list_display = ("id", "login", "user_role", "dk", "salt")

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ("id", "description")

@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ("id", "first_name", "last_name", "email", "birth_date", "registered_at")