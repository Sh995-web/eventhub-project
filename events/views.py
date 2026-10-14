from rest_framework import viewsets
from .models import Event, Reservation
from .serializers import EventSerializer, ReservationSerializer
from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404



class EventViewSet(viewsets.ModelViewSet):
    serializer_class = EventSerializer

    def get_queryset(self):
        queryset = Event.objects.all()

        status = self.request.query_params.get("status")
        venue = self.request.query_params.get("venue")

        if status:
            queryset = queryset.filter(status=status)

        if venue:
            queryset = queryset.filter(venue__icontains=venue)

        return queryset

class ReservationViewSet(viewsets.ModelViewSet):
    serializer_class = ReservationSerializer

    def update(self, request, *args, **kwargs):
        return Response(
        {"detail": "Reservation updates are not allowed. Cancel and create a new reservation instead."},
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )
    def destroy(self, request, *args, **kwargs):
        return Response(
        {"detail": "Reservations cannot be deleted. Use the cancel endpoint instead."},
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )

    def get_queryset(self):
        queryset = Reservation.objects.select_related("event").all()

        event_id = self.request.query_params.get("event_id")

        if event_id:
            queryset = queryset.filter(event_id=event_id)

        return queryset
    
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        with transaction.atomic():
            reservation = get_object_or_404(
                Reservation.objects.select_for_update(),
                pk=pk,
            )

            if reservation.status == "cancelled":
                raise ValidationError(
                    "This reservation has already been cancelled."
                )

            event = (
                Event.objects
                .select_for_update()
                .get(pk=reservation.event_id)
            )

            reservation.status = "cancelled"
            reservation.save(update_fields=["status"])

            event.available_seats += reservation.seats_reserved
            event.save(update_fields=["available_seats"])

        return Response(
            {
                "message": "Reservation cancelled successfully.",
                "reservation_id": reservation.id,
                "available_seats": event.available_seats,
            },
            status=status.HTTP_200_OK,
        )
