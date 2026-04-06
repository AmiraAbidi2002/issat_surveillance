from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Seul l'administrateur peut accéder."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'


class IsEnseignant(BasePermission):
    """Seul un enseignant peut accéder."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'enseignant'


class IsChefDepartement(BasePermission):
    """Seul un chef de département peut accéder."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'chef_departement'


class IsAdminOrChef(BasePermission):
    """Admin OU chef de département."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'chef_departement']


class IsAdminOrReadOnly(BasePermission):
    """Admin peut tout faire, les autres peuvent seulement lire (GET)."""
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return request.user.is_authenticated
        return request.user.is_authenticated and request.user.role == 'admin'