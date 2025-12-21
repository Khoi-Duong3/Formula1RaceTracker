import fastf1
import numpy as np
import pandas as pd


class TrackData:
    def __init__(self, year, location, session_type):
        self.year = year
        self.location = location
        self.session_type = session_type
        self.points = []
        self.world_x = None
        self.world_y = None
        self.driver_code = None
        self.lap_times = []  # Store lap durations
        self.rotation_angle = 0

        self.load_and_process()

    def load_and_process(self):
        print(f"Loading {self.year} {self.location} GP...")
        fastf1.Cache.enable_cache('cache') 
        session = fastf1.get_session(self.year, self.location, self.session_type)            
        session.load(telemetry=True, weather=False)

        # Get P1 driver (winner)
        race_results = session.results
        p1_driver = race_results.iloc[0]
        self.driver_code = p1_driver['Abbreviation']
        driver_number = p1_driver['DriverNumber']
        
        print(f"Loading laps for P1: {self.driver_code} (#{driver_number})")
        
        # Get all laps for P1 driver
        driver_laps = session.laps.pick_driver(driver_number)
        
        # Get first lap telemetry for track path
        first_lap = driver_laps.iloc[0]
        telemetry = first_lap.get_telemetry()
        
        circuit_info = session.get_circuit_info()
        angle = np.radians(circuit_info.rotation)
        self.rotation_angle = angle
        
        c, s = np.cos(angle), np.sin(angle)
        raw_x = telemetry['X'].values
        raw_y = telemetry['Y'].values
        
        # Rotated world coordinates for track path
        self.world_x = raw_x * c - raw_y * s
        self.world_y = raw_x * s + raw_y * c
        
        # Extract lap times (in seconds)
        for idx, lap in driver_laps.iterrows():
            if pd.notna(lap['LapTime']):
                lap_time_seconds = lap['LapTime'].total_seconds()
                self.lap_times.append(lap_time_seconds)
                print(f"  Lap {lap['LapNumber']}: {lap_time_seconds:.3f}s")
        
        print(f"Total laps: {len(self.lap_times)}")
        print(f"Total race time: {sum(self.lap_times):.1f}s")
        
    def generate_screen_points(self, screen_width, screen_height):
        
        min_x, max_x = self.world_x.min(), self.world_x.max()
        min_y, max_y = self.world_y.min(), self.world_y.max()

        track_w = max_x - min_x
        track_h = max_y - min_y

        scale = min(screen_width / track_w, screen_height / track_h) * 0.7

        x_offset = (screen_width - track_w * scale) / 2
        y_offset = (screen_height - track_h * scale) / 2

        self.points = []
        for i in range(len(self.world_x)):
            px = (self.world_x[i] - min_x) * scale + x_offset
            py = screen_height - ((self.world_y[i] - min_y) * scale + y_offset)
            self.points.append((px, py))
            
        return self.points