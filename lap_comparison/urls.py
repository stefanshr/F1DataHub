from django.urls import path
from .views import RacingVenuesView, DriversFromVenueView, SessionsFromVenueView, LapsFromDriver, TrackMapFromVenue, \
    DriverDataFromVenue

urlpatterns = [
    path('racing_venues/<int:year>/', RacingVenuesView.as_view(), name='get_racing_venues'),
    path('drivers/<int:year>/<str:venue>/<str:session_type>/', DriversFromVenueView.as_view(),
         name='get_drivers_from_venue'),
    path('sessions_from_venue/<int:year>/<str:venue>/', SessionsFromVenueView.as_view(), name='get_sessions_from_venue'),
    path('laps/<int:year>/<str:venue>/<str:session_type>/<int:driver_number>/', LapsFromDriver.as_view(),
         name='get_laps_from_driver'),
    path('track_map/<int:year>/<str:venue>/<str:session_type>/', TrackMapFromVenue.as_view(),
         name='get_track_map_from_venue'),
    path('driver_data/<int:year>/<str:venue>/<str:session_type>/<int:first_driver_number>/<int:first_lap_number>/'
         '<int:second_driver_number>/<int:second_lap_number>/',
         DriverDataFromVenue.as_view(), name='get_driver_data_from_venue')
]
