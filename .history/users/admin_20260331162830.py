from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Departement, Enseignant


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'email', 'first_name', 'last_name', 'role']
    list_filter   = ['role']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    fieldsets = UserAdmin.fieldsets + (
        ('Rôle ISSAT', {'fields': ('role',)}),
    )


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display  = ['nom', 'chef']
    search_fields = ['nom']


@admin.register(Enseignant)
class EnseignantAdmin(admin.ModelAdmin):
    list_display  = ['user', 'departement', 'heures_enseignement',
                     'heures_surveillance_dues', 'heures_effectuees']
    list_filter   = ['departement']
    search_fields = ['user__first_name', 'user__last_name', 'user__username']
    readonly_fields = ['heures_effectuees']