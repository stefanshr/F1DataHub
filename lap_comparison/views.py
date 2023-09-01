from rest_framework.views import APIView
from rest_framework.response import Response
import fastf1 as ff1
from datetime import datetime
import numpy as np

from lap_comparison.services.driver_service import fetch_drivers


class RacingVenuesView(APIView):
    def get(self, request, year, *args, **kwargs):
        ff1.Cache.enable_cache("cache")

        # Fetch the event schedule for the given year
        event_schedule = ff1.get_event_schedule(year=year, include_testing=False)
        event_dict = event_schedule.to_dict()

        past_events = []

        for event_key in event_dict['EventName'].keys():
            session1_date_utc = event_dict['Session1DateUtc'][event_key]

            if datetime.utcnow() > session1_date_utc:
                past_events.append(event_dict['EventName'][event_key])

        past_events.reverse()

        return Response(past_events)


class SessionsFromVenueView(APIView):
    def get(self, request, year, venue, *args, **kwargs):
        ff1.Cache.enable_cache("cache")

        # Fetch the event for the given year and venue
        event = ff1.get_event(year, venue)

        # Convert the event object to a dictionary
        event_dict = event.to_dict()

        # Retrieve the session names
        session_names = []
        for key, value in event_dict.items():
            if 'Session' in key and isinstance(value, str):
                if datetime.utcnow() > event_dict[key + "DateUtc"]:
                    session_names.append(value)

        session_names.reverse()

        return Response(session_names)


class DriversFromVenueView(APIView):
    def get(self, request, year, venue, session_type, *args, **kwargs):
        drivers = fetch_drivers(year, venue, session_type)
        return Response(list(drivers))


class LapsFromDriver(APIView):
    def get(self, request, year, venue, session_type, driver_number, *args, **kwargs):
        ff1.Cache.enable_cache("cache")

        session = ff1.get_session(year, gp=venue, identifier=session_type)
        session.load(laps=True, telemetry=False, weather=False, messages=True)

        driver_laps = session.laps[session.laps['DriverNumber'] == str(driver_number)]

        filtered_driver_laps = []

        for _, row in driver_laps.iterrows():
            filtered_driver_laps.append({
                'lapTime': row['LapTime'],
                'lapNumber': row['LapNumber'],
                'compound': row['Compound'],
                'tyreLife': row['TyreLife'],
                'deleted': row['Deleted']
            })

        return Response(filtered_driver_laps)


class TrackMapFromVenue(APIView):
    def rotate(self, xy, *, angle):
        rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                            [-np.sin(angle), np.cos(angle)]])
        return np.matmul(xy, rot_mat)

    def get(self, request, year, venue, session_type, *args, **kwargs):
        ff1.Cache.enable_cache("cache")
        session = ff1.get_session(year, gp=venue, identifier=session_type)
        session.load()
        lap = session.laps.pick_fastest()
        pos = lap.get_telemetry()
        pos.add_distance()

        track_data = []

        circuit_info = session.get_circuit_info()
        track_angle = circuit_info.rotation / 180 * np.pi

        for _, row in pos.iterrows():
            rotated_point = self.rotate([row['X'], row['Y']], angle=track_angle)
            track_data.append({
                'x': rotated_point[0],
                'y': rotated_point[1],
                'z': row['Z'],
                'distance': row['Distance']
            })

        corners_data = []
        offset_vector = [500, 0]
        for _, corner in circuit_info.corners.iterrows():
            offset_angle = corner['Angle'] / 180 * np.pi
            offset_x, offset_y = self.rotate(offset_vector, angle=offset_angle)
            text_x = corner['X'] + offset_x
            text_y = corner['Y'] + offset_y
            text_x, text_y = self.rotate([text_x, text_y], angle=track_angle)
            track_x, track_y = self.rotate([corner['X'], corner['Y']], angle=track_angle)
            corners_data.append({
                'corner_number': f"{corner['Number']}{corner['Letter']}",
                'text_position': [text_x, text_y],
                'track_position': [track_x, track_y]
            })
        data = {
            'track': track_data,
            'corners': corners_data
        }
        return Response(data)


class DriverDataFromVenue(APIView):
    def rotate(self, xy, *, angle):
        rot_mat = np.array([[np.cos(angle), np.sin(angle)],
                            [-np.sin(angle), np.cos(angle)]])
        return np.matmul(xy, rot_mat)

    def get(self, request, year, venue, session_type, driver_number, lap_number, *args, **kwargs):
        ff1.Cache.enable_cache("cache")
        session = ff1.get_session(year, gp=venue, identifier=session_type)
        session.load()

        # Get circuit rotation angle
        circuit_info = session.get_circuit_info()
        track_angle = circuit_info.rotation / 180 * np.pi

        lap = session.laps.pick_lap(lap_number).pick_driver(driver_number)
        telemetry_car_pos = lap.get_telemetry()
        telemetry_car_pos.add_distance()

        telemetry_data = []
        for _, row in telemetry_car_pos.iterrows():
            rotated_point = self.rotate([row['X'], row['Y']], angle=track_angle)
            telemetry_data.append({
                'timestamp': row['Time'],
                'x': rotated_point[0],
                'y': rotated_point[1],
                'z': row['Z'],
                'status': row['Status'],
                'throttle': row['Throttle'],
                'brake': row['Brake'],
                'speed': row['Speed'],
                'gear': row['nGear'],
                'rpm': row['RPM'],
                'drs': row['DRS'],
                'distance': row['Distance']
            })

        lap_data = {
            'lapNumber': lap_number,
            'driver': next((driver for driver in fetch_drivers(year, venue, session_type) if
                            driver['driverNumber'] == str(driver_number)), None),
            'lapTime': lap['LapTime'],
            'compound': lap['Compound'],
            'deleted': lap['Deleted'],
            'deletedReason': lap['DeletedReason'],
            'tyreLife': lap['TyreLife'],
            'stint': lap['Stint'],
            'sector1Time': lap['Sector1Time'],
            'sector2Time': lap['Sector2Time'],
            'sector3Time': lap['Sector3Time'],
            'telemetryData': telemetry_data
        }

        return Response(lap_data)
