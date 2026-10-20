from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import GroupProfile, User


class GroupProfileInline(admin.StackedInline):
    model = GroupProfile
    can_delete = False
    readonly_fields = ["terms_accepted_at", "created_at"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "is_active", "is_staff", "date_joined", "last_login"]
    list_filter = ["is_active", "is_staff"]
    search_fields = ["email"]
    inlines = [GroupProfileInline]
    fieldsets = [
        (None, {"fields": ["email", "password"]}),
        ("Rechte", {"fields": ["is_active", "is_staff", "is_superuser", "groups", "user_permissions"]}),
        ("Daten", {"fields": ["last_login", "date_joined"]}),
    ]
    add_fieldsets = [(None, {"classes": ["wide"], "fields": ["email", "password1", "password2"]})]


@admin.register(GroupProfile)
class GroupProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "district", "status", "created_at"]
    list_filter = ["status", "kind", "district"]
    search_fields = ["name", "user__email"]
    readonly_fields = ["user", "terms_accepted_at", "created_at"]
    actions = ["approve", "block"]

    @admin.action(description="Freischalten")
    def approve(self, request, queryset):
        n = queryset.update(status=GroupProfile.Status.APPROVED)
        self.message_user(request, f"{n} Gruppe(n) freigeschaltet.", messages.SUCCESS)

    @admin.action(description="Sperren")
    def block(self, request, queryset):
        n = queryset.update(status=GroupProfile.Status.BLOCKED)
        self.message_user(request, f"{n} Gruppe(n) gesperrt.", messages.WARNING)
