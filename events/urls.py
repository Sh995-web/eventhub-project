from rest_framework.routers import DefaultRouter
from .views import EventViewSet, ReservationViewSet

router = DefaultRouter()
router.register("events", EventViewSet, basename="event")
router.register("reservations", ReservationViewSet, basename="reservation")

urlpatterns = router.urls
