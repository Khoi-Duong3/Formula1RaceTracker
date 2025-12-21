import fastf1
import numpy as np
import pandas as pd
from scipy import interpolate

class RaceData:
    def __init__(self, year, location, session_type):
        self.year = year
        self.location = location
        self.session_type = session_type
        self.session = None
        self.drivers = []
        self.driver_data = {}
        self.track_x = None
        self.track_y = None
        self.frames = []
        self.frame_interval = 0.1

        self.load_session()
        self.load_track()
        self.load_drivers()
        self.generate_frames()

    def load_session(self):
        print(f"Loading {self.location} {self.year} {self.session_type}")
        fastf1.Cache.enable_cache('cache')
        self.session = fastf1.get_session(self.year, self.location, self.session_type)
        self.session.load(telemetry=True, weather=False, laps=True)
        print(f"Session loaded: {self.session.event['EventName']}")
    
    def load_track(self):
        fastest_lap = self.session.laps.pick_fastest()
        telemetry = fastest_lap.get_telemetry()
        circuit_info = self.session.get_circuit_info()
        angle = np.radians(circuit_info.rotation)
        cos, sin = np.cos(angle), np.sin(angle)

        raw_x = telemetry["X"].values
        raw_y = telemetry["Y"].values
        self.track_x = raw_x * cos - raw_y * sin
        self.track_y = raw_x * sin + raw_y * cos

        print(f"Track loaded: {len(self.track_x)} points")
    

    def load_drivers(self):
        print(f"Loading driver data...")
        self.drivers = self.session.drivers

        circuit_info = self.session.get_circuit_info()
        angle = np.radians(circuit_info.rotation)
        cos, sin = np.cos(angle), np.sin(angle)

        for driver_number in self.drivers:
            driver_info = self.session.get_driver(driver_number)
            abbreviation = driver_info["Abbreviation"]
            team_colour_hex = driver_info.get("TeamColor", "FFFFFF")
            try:
                driver_laps = self.session.laps.pick_drivers(driver_number)

                if driver_laps.empty:
                    continue
                
                all_telemetry = []
                for lap in driver_laps.iterlaps():
                    tele = lap[1].get_telemetry()
                    if tele is not None and not tele.empty:
                        all_telemetry.append(tele)
                    
                if not all_telemetry:
                    continue

                full_telemetry = pd.concat(all_telemetry, ignore_index=True)

                timestamps = full_telemetry["Time"].dt.total_seconds().values
                raw_x = full_telemetry['X'].values
                raw_y = full_telemetry['Y'].values

                rotated_x = raw_x * cos - raw_y * sin
                rotated_y = raw_x * sin + raw_y * cos

                timestamps = timestamps - timestamps[0]

                self.driver_data[driver_number] = {
                    "abbreviation": abbreviation,
                    "timestamps": timestamps,
                    "x": rotated_x,
                    "y": rotated_y,
                    "colour": self.hex_to_rgb(team_colour_hex),
                    "team": driver_info.get("TeamName", "Unknown")
                }
            except Exception as e:
                print(f"  Skipping {abbreviation}: {e}")

        print(f"Loaded {len(self.driver_data)} drivers")

    def generate_frames(self):
        print(f"Generating frames...")

        max_time = 0
        for driver_number, data in self.driver_data.items():
            if data["timestamps"][-1] > max_time:
                max_time = data["timestamps"][-1]
        
        current_time = 0
        while current_time <= max_time:
            frame = {
                "time": current_time,
                "drivers": {}
            }
        
            for driver_num, data in self.driver_data.items():
                if current_time <= data["timestamps"][-1]:
                    x_pos = np.interp(current_time, data["timestamps"], data["x"])
                    y_pos = np.interp(current_time, data["timestamps"], data["y"])

                    frame["drivers"][driver_number] = {
                        'x': x_pos,
                        'y': y_pos,
                        'abbreviation': data['abbreviation'],
                        'colour': data['colour'],
                        'active': True
                    }
                else:
                    frame['drivers'][driver_num] = {
                        'x': data['x'][-1],
                        'y': data['y'][-1],
                        'abbreviation': data['abbreviation'],
                        'colour': data['colour'],
                        'active': False
                    }
            self.frames.append(frame)
            current_time += self.frame_interval
        
        print(f"Generated {len(self.frames)} frames ({max_time:.1f}s race duration)")

    def hex_to_rgb(self, hex_colour):
        hex_colour = hex_colour.lstrip("#")
        return tuple(int(hex_colour[i: i+ 2], 16) for i in (0, 2, 4))