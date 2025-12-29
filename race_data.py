import fastf1
import numpy as np
import pandas as pd


class RaceData:
    def __init__(self, year, location, session_type):
        self.year = year
        self.location = location
        self.session_type = session_type
        self.session = None
        self.drivers = []
        self.driver_data = {}
        self.driver_compounds = {}
        self.track_x = None
        self.track_y = None
        self.track_length = None
        self.track_s = None
        self.frames = []
        self.frame_interval = 0.1
        self.global_start = None
        self.lap_timeline = None
        self.position_timeline = {}
        self.last_visual_order = None
        self.last_visual_time = -1.0

        self.load_session()
        self.build_compound_map()
        self.load_track()
        self.build_track_distancee()
        self.load_drivers()
        self.build_lap_timeline()
        self.align_timelines_and_generate_frames()
        self.build_position_timeline()

    def load_session(self):
        print(f"Loading {self.location} {self.year} {self.session_type}")
        fastf1.Cache.enable_cache("cache")
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
        print("Loading driver data...")
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

                full_telemetry = driver_laps.get_telemetry()
                if full_telemetry is None or full_telemetry.empty:
                    continue
                
                if "LapNumber" in full_telemetry.columns:
                    lap_numbers = full_telemetry["LapNumber"].values
                else:
                    lap_numbers = np.ones(len(full_telemetry), dtype=int)
                
                # Use session-relative time, not per-lap Time
                if "SessionTime" in full_telemetry.columns:
                    timestamps = (
                        full_telemetry["SessionTime"].dt.total_seconds().values
                    )
                else:
                    timestamps = full_telemetry["Time"].dt.total_seconds().values

                raw_x = full_telemetry["X"].values
                raw_y = full_telemetry["Y"].values

                rotated_x = raw_x * cos - raw_y * sin
                rotated_y = raw_x * sin + raw_y * cos

                self.driver_data[driver_number] = {
                    "abbreviation": abbreviation,
                    "timestamps": timestamps,  # still absolute here
                    "x": rotated_x,
                    "y": rotated_y,
                    "lap_numbers": lap_numbers,
                    "colour": self.hex_to_rgb(team_colour_hex),
                    "team": driver_info.get("TeamName", "Unknown"),
                }

            except Exception as e:
                print(f"  Skipping {abbreviation}: {e}")

        print(f"Loaded {len(self.driver_data)} drivers")

    def hex_to_rgb(self, hex_colour):
        hex_colour = hex_colour.lstrip("#")
        return tuple(int(hex_colour[i : i + 2], 16) for i in (0, 2, 4))

    def build_lap_timeline(self):
        laps = self.session.laps.copy()
        laps = laps.loc[~laps["LapStartTime"].isna()]
       
        p1 = laps[laps["Position"] == 1.0]
        if not p1.empty:
            leader_laps = p1
        else:
            default_number = laps["DriverNumber"].iloc[0]
            leader_laps = laps[laps["DriverNumber"] == default_number]
        
        if "LapStartSessionTime" in leader_laps.columns:
            leader_laps["lap_start_s"] = (leader_laps["LapStartSessionTime"].dt.total_seconds())
        else:
            leader_laps["lap_start_s"] = (leader_laps["LapStartTime"].dt.total_seconds())

        leader_laps = leader_laps.sort_values("LapNumber")
        lap_numbers = leader_laps["LapNumber"].to_numpy(dtype=int)
        start_times = leader_laps["lap_start_s"].to_numpy()
        end_times = np.empty_like(start_times, dtype=float)
        end_times[:-1] = start_times[1:]

        latest_time = max(max(d["timestamps"]) for d in self.driver_data.values())
        end_times[-1] = latest_time

        self.lap_timeline = list(zip(start_times, end_times, lap_numbers))

    def lap_for_time(self, time):
        session_time = time + self.global_start
        for start, end, lap_num in self.lap_timeline:
            if start <= session_time < end:
                return int(lap_num)

        return int(self.lap_timeline[-1][2])

    def align_timelines_and_generate_frames(self):
        print("Aligning timelines and generating frames...")

        if not self.driver_data:
            print("No driver data available.")
            return

        # Global session-based start and end
        global_start = min(d["timestamps"][0] for d in self.driver_data.values())
        global_end = max(d["timestamps"][-1] for d in self.driver_data.values())
        race_duration = global_end - global_start

        self.global_start = global_start

        # Normalise each driver timeline so replay time starts at 0
        for d in self.driver_data.values():
            d["timestamps"] = d["timestamps"] - global_start

        max_time = race_duration
        print(
            f"Race duration (session-relative): {race_duration:.1f}s, "
            f"frame interval: {self.frame_interval:.2f}s"
        )

        current_time = 0.0
        while current_time <= max_time:
            frame_lap = self.lap_for_time(current_time)
            frame = {
                "time": current_time,
                "drivers": {},
            }

            for driver_number, data in self.driver_data.items():
                ts = data["timestamps"]

                if current_time <= ts[-1]:
                    x_pos = np.interp(current_time, ts, data["x"])
                    y_pos = np.interp(current_time, ts, data["y"])

                    active = True
                else:
                    x_pos = data["x"][-1]
                    y_pos = data["y"][-1]
                    lap = int(data["lap_numbers"][-1])
                    active = False

                frame["drivers"][driver_number] = {
                    "x": x_pos,
                    "y": y_pos,
                    "lap": frame_lap,
                    "abbreviation": data["abbreviation"],
                    "colour": data["colour"],
                    "active": active,
                }

            self.frames.append(frame)
            current_time += self.frame_interval

        print(
            f"Generated {len(self.frames)} frames "
            f"({max_time:.1f}s race duration)"
        )

    def build_position_timeline(self):
        laps = self.session.laps.copy()
        laps = laps.loc[~laps["LapStartTime"].isna()]

        if "LapStartSessionTime" in laps.columns:
            laps["lap_start_s"] = laps["LapStartSessionTime"].dt.total_seconds()
        else:
            laps["lap_start_s"] = laps["LapStartTime"].dt.total_seconds()
        
        laps = laps.sort_values(["DriverNumber", "LapNumber"])

        for driver, driver_laps in laps.groupby("DriverNumber"):
            driver_laps = driver_laps.sort_values("LapNumber")
            start_times = driver_laps["lap_start_s"].to_numpy()
            lap_nums = driver_laps["LapNumber"].astype(int).to_numpy()
            positions = driver_laps["Position"].to_numpy()

            if len(start_times) == 0 or (positions.size > 0 and all(pd.isna(positions))):
                continue

            end_times = np.empty_like(start_times, dtype=float)
            end_times[:-1] = start_times[1:]

            if driver in self.driver_data:
                last = self.driver_data[driver]["timestamps"].max() + self.global_start
            else:
                last = start_times[-1] + 200.0 
            
            end_times[-1] = last

            segments = []
            for start, end, pos, lap in zip(start_times, end_times, positions, lap_nums):
                if np.isnan(pos):
                    continue
                segments.append((float(start), float(end), int(pos), int(lap)))
            
            self.position_timeline[driver] = segments

    def get_leaderboard(self, replay_time_s):
        session_time = replay_time_s + self.global_start

        standings = []

        for driver, segments in self.position_timeline.items():
            pos_now = None
            lap_now = None

            for start, end, pos, lap in segments:
                if start <= session_time < end:
                    pos_now = pos
                    lap_now = lap
                    break
            
            is_dnf = False

            if pos_now is None:
                if segments and session_time > segments[-1][1]:
                    is_dnf = True
                    pos_now = segments[-1][2]
                    lap_now = segments[-1][3]
                else:
                    continue

            info = self.session.get_driver(driver)
            abbreviation = info["Abbreviation"]
            current_compound = "UNKNOWN"
            if str(driver) in self.driver_compounds:
                current_compound = self.driver_compounds[str(driver)].get(lap_now, "UNKNOWN")
            
            sort_pos = 1000 + pos_now if is_dnf else pos_now

            standings.append({
                "Position": pos_now,
                "SortKey": sort_pos,
                "driver_number": str(driver),
                "Abbreviation": abbreviation,
                "lap": lap_now,
                "team": info.get("TeamName", "Unknown"),
                "Compound" : current_compound,
                "DNF": is_dnf
            })
           
        standings.sort(key=lambda d: d["Position"])
        return standings

    def build_compound_map(self):
        self.driver_compounds = {}
        if self.session and hasattr(self.session, "laps"):
            present_laps = self.session.laps[["DriverNumber", "LapNumber", "Compound"]].dropna()
            for _,row in present_laps.iterrows():
                driver_num = str(int(row["DriverNumber"]))
                lap_number = int(row["LapNumber"])
                compound = row["Compound"]

                if driver_num not in self.driver_compounds:
                    self.driver_compounds[driver_num] = {}
                
                self.driver_compounds[driver_num][lap_number] = compound
    
    def build_track_distancee(self):
        track_x = self.track_x
        track_y = self.track_y

        seg_dx = np.diff(track_x)
        seg_dy = np.diff(track_y)
        seg_len = np.sqrt((seg_dx)**2 + (seg_dy)**2)
        cumulative_distances = np.concatenate(([0.0], np.cumsum(seg_len)))
        self.track_s = cumulative_distances
        self.track_length = cumulative_distances[-1]

    def project_to_track_position(self, x, y):
        dx = self.track_x - x
        dy = self.track_y - y
        index = np.argmin(dx * dx + dy * dy)
        return self.track_s[index]
    
    def get_visual_leaderboard(self, current_replay_time, min_dt=0.5):
        if self.last_visual_order is not None:
            if current_replay_time - self.last_visual_time < min_dt:
                return self.last_visual_order
        
        frame_index = int(current_replay_time / self.frame_interval)
        frame_index = max(0, min(frame_index, len(self.frames) - 1))
        frame = self.frames[frame_index]

        entries = []
        for driver, data in frame["drivers"].items():
            # if not data["active"]:
                # continue
            x = data["x"]
            y = data["y"]
            projected = self.project_to_track_position(x, y)
            projected = round(projected/5.0) * 5.0

            entries.append({
                "Position": None,              
                "driver_number": str(driver),
                "Abbreviation": data["abbreviation"],
                "lap": data["lap"],
                "projected": projected,
            })

        entries.sort(key=lambda e: e["projected"], reverse=True)

        for i, e in enumerate(entries, start=1):
            e["Position"] = i

        if self.last_visual_order is not None:
            last_drivers = [e["driver_number"] for e in self.last_visual_order]
            new_drivers = [e["driver_number"] for e in entries]
            if new_drivers == last_drivers:
                return self.last_visual_order

        self.last_visual_order = entries
        self.last_visual_time = current_replay_time
        return entries

    
