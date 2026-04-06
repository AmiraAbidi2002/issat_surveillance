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

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        return attrs

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
    chef_nom = serializers.SerializerMethodField()

    class Meta:
        model = Departement
        fields = ['id', 'nom', 'chef', 'chef_nom']

    def get_chef_nom(self, obj):
        return str(obj.chef) if obj.chef else None


class EnseignantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )
    departement_nom = serializers.SerializerMethodField()
    heures_restantes = serializers.ReadOnlyField()

    class Meta:
        model = Enseignant
        fields = [
            'id', 'user', 'user_id', 'departement', 'departement_nom',
            'heures_enseignement', 'heures_surveillance_dues',
            'heures_effectuees', 'heures_restantes'
        ]

    def get_departement_nom(self, obj):
        return obj.departement.nom if obj.departement else None


class EnseignantCreateSerializer(serializers.Serializer):
    """Crée un User + Enseignant en une seule requête (utilisé par l'admin)."""
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    password = serializers.CharField(write_only=True)
    departement_id = serializers.IntegerField()
    heures_enseignement = serializers.FloatField()

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def create(self, validated_data):
        departement = Departement.objects.get(id=validated_data['departement_id'])
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            password=validated_data['password'],
            role='enseignant'
        )
        enseignant = Enseignant.objects.create(
            user=user,
            departement=departement,
            heures_enseignement=validated_data['heures_enseignement'],
            heures_surveillance_dues=validated_data['heures_enseignement']
        )
        return enseignant