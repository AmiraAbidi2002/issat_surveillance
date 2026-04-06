from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Departement, Enseignant


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role']
        read_only_fields = ['id']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'role', 'password', 'password2']

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Ancien mot de passe incorrect.")
        return value

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()


class DepartementSerializer(serializers.ModelSerializer):
    chef_nom = serializers.CharField(source='chef.get_full_name', read_only=True)

    class Meta:
        model = Departement
        fields = ['id', 'nom', 'chef', 'chef_nom']


class EnseignantSerializer(serializers.ModelSerializer):
    # Infos de l'utilisateur lié (lecture)
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='enseignant'),
        source='user',
        write_only=True
    )
    departement_nom = serializers.CharField(source='departement.nom', read_only=True)
    heures_restantes = serializers.FloatField(read_only=True)

    class Meta:
        model = Enseignant
        fields = [
            'id', 'user', 'user_id', 'departement', 'departement_nom',
            'heures_enseignement', 'heures_surveillance_dues',
            'heures_effectuees', 'heures_restantes'
        ]
        read_only_fields = ['heures_surveillance_dues', 'heures_effectuees']


class EnseignantCreateSerializer(serializers.Serializer):
    """Crée un User + Enseignant en une seule requête (utilisé par l'admin)."""
    username        = serializers.CharField()
    email           = serializers.EmailField()
    first_name      = serializers.CharField()
    last_name       = serializers.CharField()
    password        = serializers.CharField(write_only=True)
    departement_id  = serializers.IntegerField()
    heures_enseignement = serializers.FloatField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate_departement_id(self, value):
        if not Departement.objects.filter(id=value).exists():
            raise serializers.ValidationError("Département introuvable.")
        return value

    def create(self, validated_data):
        dept_id = validated_data.pop('departement_id')
        heures  = validated_data.pop('heures_enseignement')

        # Créer le User
        user = User.objects.create_user(
            role='enseignant',
            **validated_data
        )
        # Créer le profil Enseignant
        enseignant = Enseignant.objects.create(
            user=user,
            departement_id=dept_id,
            heures_enseignement=heures,
            heures_surveillance_dues=heures   # Au départ = heures enseignement
        )
        return enseignant