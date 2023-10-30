from rest_framework.views import APIView
from rest_framework.response import Response
import fastf1 as ff1
from datetime import datetime
import numpy as np

from lap_comparison.services.driver_service import fetch_drivers


class RacingVenuesView(APIView):
    def get(self, request, year, *args, **kwargs):
        ff1.Cache.enable_cache("cache")

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

        event = ff1.get_event(year, venue)
        event_dict = event.to_dict()
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

    def segment_by_distance(self, telemetry_data, n_segments):
        total_distance = telemetry_data[-1]['distance']
        segment_length = total_distance / n_segments
        segmented_data = []
        indices = []
        start_idx = 0

        for i in range(1, n_segments + 1):
            target_distance = i * segment_length
            for end_idx, point in enumerate(telemetry_data[start_idx:], start=start_idx):
                if point['distance'] >= target_distance:
                    segmented_data.append(telemetry_data[start_idx:end_idx])
                    indices.append({'start': start_idx, 'end': end_idx})
                    start_idx = end_idx
                    break

        return segmented_data, indices

    def get(self, request, year, venue, session_type, first_driver_number, first_lap_number, second_driver_number,
            second_lap_number, *args, **kwargs):
        ff1.Cache.enable_cache("cache")
        session = ff1.get_session(year, gp=venue, identifier=session_type)
        session.load()

        circuit_info = session.get_circuit_info()
        track_angle = circuit_info.rotation / 180 * np.pi

        first_lap = session.laps.pick_lap(first_lap_number).pick_driver(first_driver_number)
        first_telemetry_car_pos = first_lap.get_telemetry()
        first_telemetry_car_pos.add_distance()

        first_telemetry_data = []
        for _, row in first_telemetry_car_pos.iterrows():
            rotated_point = self.rotate([row['X'], row['Y']], angle=track_angle)
            first_telemetry_data.append({
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

        first_lap_data = {
            'lapNumber': first_lap_number,
            'driver': next((driver for driver in fetch_drivers(year, venue, session_type) if
                            driver['driverNumber'] == str(first_driver_number)), None),
            'lapTime': first_lap['LapTime'],
            'compound': first_lap['Compound'],
            'deleted': first_lap['Deleted'],
            'deletedReason': first_lap['DeletedReason'],
            'tyreLife': first_lap['TyreLife'],
            'stint': first_lap['Stint'],
            'sector1Time': first_lap['Sector1Time'],
            'sector2Time': first_lap['Sector2Time'],
            'sector3Time': first_lap['Sector3Time'],
            'telemetryData': first_telemetry_data
        }

        second_lap = session.laps.pick_lap(second_lap_number).pick_driver(second_driver_number)
        second_telemetry_car_pos = second_lap.get_telemetry()
        second_telemetry_car_pos.add_distance()

        second_telemetry_data = []

        for _, row in second_telemetry_car_pos.iterrows():
            rotated_point = self.rotate([row['X'], row['Y']], angle=track_angle)
            second_telemetry_data.append({
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

        second_lap_data = {
            'lapNumber': second_lap_number,
            'driver': next((driver for driver in fetch_drivers(year, venue, session_type) if
                            driver['driverNumber'] == str(second_driver_number)), None),
            'lapTime': second_lap['LapTime'],
            'compound': second_lap['Compound'],
            'deleted': second_lap['Deleted'],
            'deletedReason': second_lap['DeletedReason'],
            'tyreLife': second_lap['TyreLife'],
            'stint': second_lap['Stint'],
            'sector1Time': second_lap['Sector1Time'],
            'sector2Time': second_lap['Sector2Time'],
            'sector3Time': second_lap['Sector3Time'],
            'telemetryData': second_telemetry_data
        }

        n_segments = 12

        first_segmented_data, first_indices = self.segment_by_distance(first_telemetry_data, n_segments)
        second_segmented_data, second_indices = self.segment_by_distance(second_telemetry_data, n_segments)

        faster_driver_segments = []

        for i, (first_segment, second_segment) in enumerate(zip(first_segmented_data, second_segmented_data)):
            first_time = first_segment[-1]['timestamp'] - first_segment[0]['timestamp']
            second_time = second_segment[-1]['timestamp'] - second_segment[0]['timestamp']

            if first_time < second_time:
                faster_driver = first_driver_number
            else:
                faster_driver = second_driver_number

            faster_driver_segments.append({
                'fasterDriver': faster_driver,
                'firstDriverIndices': first_indices[i],
                'secondDriverIndices': second_indices[i]
            })

        response_data = {
            'firstLapData': first_lap_data,
            'secondLapData': second_lap_data,
            'fasterDriverBySegment': faster_driver_segments
        }

        return Response(response_data)
