from django.db import transaction
from rest_framework import serializers
from .models import Event, Reservation


class EventSerializer(serializers.ModelSerializer):
    reservations_count = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "venue",
            "date",
            "total_seats",
            "available_seats",
            "status",
            "created_at",
            "reservations_count",
        ]
        read_only_fields = [
     "id",
    "created_at",
    "reservations_count",
    "available_seats",
]
    def get_reservations_count(self, obj):
        return obj.reservations.filter(status="confirmed").count()

    def validate(self, attrs):
        total_seats = attrs.get(
            "total_seats",
            getattr(self.instance, "total_seats", None),
        )

        if self.instance is not None and total_seats is not None:
            confirmed_seats = sum(
                self.instance.reservations.filter(
                    status="confirmed"
                ).values_list("seats_reserved", flat=True)
            )

            available_seats = self.instance.available_seats

            if total_seats < confirmed_seats + available_seats:
                raise serializers.ValidationError({
                    "total_seats": (
                        "Total seats cannot be less than "
                        "reserved seats plus available seats."
                    )
                })

        return attrs
    
    def create(self, validated_data):
        validated_data["available_seats"] = validated_data["total_seats"]
        return Event.objects.create(**validated_data)


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = [
            "id",
            "event",
            "attendee_name",
            "attendee_email",
            "seats_reserved",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_seats_reserved(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "At least one seat must be reserved."
            )
        return value

    def validate(self, attrs):
        event = attrs.get("event")

        if event is None:
            return attrs

        if event.status not in ["upcoming", "ongoing"]:
            raise serializers.ValidationError({
                "event": "Reservations are allowed only for upcoming or ongoing events."
            })

        seats_reserved = attrs.get("seats_reserved", 0)

        if seats_reserved > event.available_seats:
            raise serializers.ValidationError({
                "seats_reserved": "Not enough seats available."
            })

        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            event = Event.objects.select_for_update().get(
                pk=validated_data["event"].pk
            )

            if event.status not in ["upcoming", "ongoing"]:
                raise serializers.ValidationError({
                    "event": "Reservations are not allowed for this event."
                })

            seats_reserved = validated_data["seats_reserved"]

            if seats_reserved > event.available_seats:
                raise serializers.ValidationError({
                    "seats_reserved": "Not enough seats available."
                })

            reservation = Reservation.objects.create(**validated_data)

            event.available_seats -= seats_reserved
            event.save(update_fields=["available_seats"])

            return reservation

