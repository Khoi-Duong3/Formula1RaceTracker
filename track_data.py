import fastf1
import numpy as np

class TrackData:
    def __init__(self, year, location, session_type):
        self.year = year
        self.location = location
        self.session_type = session_type
        self.points = []
        self.world_x = None
        self.world_y = None

        self.load_and_process()

    def load_and_process(self):
        print(f"Loading {self.year} {self.location} GP...")
        fastf1.Cache.enable_cache('cache') 
        session = fastf1.get_session(self.year, self.location, self.session_type)            
        session.load(telemetry=True, weather=False)

        fastest_lap = session.laps.pick_fastest()
        fastest_lap_telemetry = fastest_lap.get_telemetry()

        circuit_info = session.get_circuit_info()
        angle = np.radians(circuit_info.rotation)

        c, s = np.cos(angle), np.sin(angle)
        raw_x = fastest_lap_telemetry['X'].values
        raw_y = fastest_lap_telemetry['Y'].values

        # Rotated world coordinates
        self.world_x = raw_x * c - raw_y * s
        self.world_y = raw_x * s + raw_y * c
        
    def generate_screen_points(self, screen_width, screen_height):
        
        min_x, max_x = self.world_x.min(), self.world_x.max()
        min_y, max_y = self.world_y.min(), self.world_y.max()

        track_w = max_x - min_x
        track_h = max_y - min_y

        scale = min(screen_width / track_w, screen_height / track_h) * 0.7

        x_offset = (screen_width - track_w * scale) / 2
        y_offset = (screen_height - track_h * scale) / 2

        self.points = []
        for i in range (len(self.world_x)):
            px = (self.world_x[i] - min_x) * scale + x_offset
            py = screen_height - ((self.world_y[i] - min_y) * scale + y_offset)
            self.points.append((px, py))
            
        return self.points
