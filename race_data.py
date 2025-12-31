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
        self.driver_status = {}
        self.pit_windows = {}
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
        self.lap_position_map = {}

        self.load_session()
        self.load_results()
        self.build_compound_map()
        self.load_track()
        self.load_drivers()
        self.build_lap_timeline()
        self.align_timelines_and_generate_frames()
        self.build_position_timeline()
        self.build_pit_windows()

    def load_session(self):
        print(f"Loading {self.location} {self.year} {self.session_type}")
        fastf1.Cache.enable_cache("cache")
        self.session = fastf1.get_session(self.year, self.location, self.session_type)
        self.session.load(telemetry=True, weather=False, laps=True)
        print(f"Session loaded: {self.session.event['EventName']}")

    def load_results(self):
        if self.session and hasattr(self.session, "results"):
            for _, row in self.session.results.iterrows():
                driver_num = str(int(row['DriverNumber']))
                status = str(row["Status"])
                is_finished = status.lower() in ['finished'] or '+' in status

                self.driver_status[driver_num] = {
                    "Status": status,
                    'is_dnf': not is_finished,
                    'grid': row.get('GridPosition', 20.0)

                }
        
        print("Driver status loaded.")

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
                
                if "SessionTime" in full_telemetry.columns:
                    timestamps = (full_telemetry["SessionTime"].dt.total_seconds().values)
                else:
                    timestamps = full_telemetry["Time"].dt.total_seconds().values

                raw_x = full_telemetry["X"].values
                raw_y = full_telemetry["Y"].values

                rotated_x = raw_x * cos - raw_y * sin
                rotated_y = raw_x * sin + raw_y * cos

                self.driver_data[driver_number] = {
                    "abbreviation": abbreviation,
                    "timestamps": timestamps,
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

    def build_lap_position_map(self):
        if self.session and hasattr(self.session, "laps"):
            valid = self.session.laps[['DriverNumber', 'LapNumber', 'Position']].dropna()

            for _, row in valid.iterrows():
                driver = str(int(row["DriverNumber"]))
                lap = int(row["LapNumber"])
                pos = int(row["Position"])

                if driver not in self.lap_position_map:
                    self.lap_position_map[driver] = {}
                
                self.lap_position_map[driver][lap] = pos

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

        if "LapStartSessionTime" in laps.columns:
            laps["lap_start_s"] = laps["LapStartSessionTime"].dt.total_seconds()
        else:
            laps["lap_start_s"] = laps["LapStartTime"].dt.total_seconds()
        
        laps = laps.sort_values(["DriverNumber", "LapNumber"])

        for driver_num in self.session.drivers:
            driver = str(driver_num)
            driver_laps = laps[laps["DriverNumber"] == driver]

            if driver_laps.empty or driver_laps["LapStartTime"].isna().all():
                start_t = self.global_start if self.global_start else 0
                grid_pos = 20
                if driver in self.driver_status:
                    grid_pos = int(self.driver_status[driver]["grid"])

                segments = [(float(start_t), float(start_t + 1.0), grid_pos, 0)]
                self.position_timeline[driver] = segments
                continue

            driver_laps = driver_laps.loc[~driver_laps["LapStartTime"].isna()]
            start_times = driver_laps["lap_start_s"].to_numpy()
            lap_nums = driver_laps["LapNumber"].astype(int).to_numpy()
            positions = driver_laps["Position"].to_numpy()

            if len(start_times) == 0:
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
        session_time = replay_time_s
        standings = []

        driver_keys = list(self.driver_status.keys())

        for driver in driver_keys:
            driver_str = str(driver)
            lap_now = 1
            is_active = False

            if driver_str in self.driver_data:
                data = self.driver_data[driver_str]
                timestamp = data["timestamps"]
                laps = data["lap_numbers"]

                if session_time < timestamp[0]:
                    lap_now = 0
                elif session_time > timestamp[-1]:
                    lap_now = int(laps[-1])
                else:
                    index = np.searchsorted(timestamp, session_time)
                    if index < len(laps):
                        lap_now = int(laps[index])
                        is_active = True
                    else:
                        lap_now = int(laps[-1])
                
            status = self.driver_status.get(driver_str, {})
            display_pos = 20
            is_dnf = status.get('is_dnf', False)

            if not is_active and driver_str in self.driver_data and session_time > self.driver_data[driver_str]['timestamps'][-1]:
                if 'Position' in status:
                    display_pos = int(status['Position'])
                else:
                    display_pos = 20
            
            elif lap_now <= 1:
                display_pos = int(status.get('grid', 20))
                if display_pos == 0: display_pos = 20

            else:
                target_lap = lap_now - 1
                if driver_str in self.lap_position_map:
                    display_pos = self.lap_position_map[driver_str].get(target_lap, int(status.get('grid', 20)))
                else:
                    display_pos = int(status.get('grid', 20))

            show_dnf = False
            if is_dnf:
                if driver_str in self.driver_data:
                    if session_time > self.driver_data[driver_str]['timestamps'][-1]:
                        show_dnf = True
                else:
                    show_dnf = True

            if show_dnf:
                sort_key = 2000 + display_pos
            else:
                sort_key = display_pos
            
            info = self.session.get_driver(driver_str)
            current_compound = "UNKNOWN"
            if driver_str in self.driver_compounds:
                current_compound = self.driver_compounds[driver_str].get(lap_now, "UNKNOWN")
            
            is_pitting = False
            if driver_str in self.pit_windows:
                for start, end in self.pit_windows[driver_str]:
                    if start <= replay_time_s <= end:
                        is_pitting = True
                        break
            
            standings.append({
                "Position": display_pos,
                "SortKey": sort_key,
                "driver_number": driver_str,
                "Abbreviation": info["Abbreviation"],
                "lap": lap_now,
                "team": info.get("TeamName", "Unknown"),
                "Compound" : current_compound,
                "DNF": show_dnf,
                "Pitting": is_pitting
            })

            if driver_str == "1": # Max's number
                print(f"VER Time: {replay_time_s:.1f} | Windows: {self.pit_windows.get(driver_str, [])}")

        standings.sort(key=lambda d: d["SortKey"])
        rank = 1
        
        for entry in standings:
            entry["Position"] = rank
            rank += 1
        
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
    
    def build_pit_windows(self):

        if self.session and hasattr(self.session, "laps"):
            pit_laps = self.session.laps[~self.session.laps["PitInTime"].isna()]

            print(f"Total Pit Stops Found in Session: {len(pit_laps)}")

            for driver in self.session.drivers:
                driver_pit_laps = pit_laps[pit_laps["DriverNumber"].astype(str).isin([str(driver)])]
                windows = []

                for _, row in driver_pit_laps.iterrows():
                    try:
                        pit_in_value = row["PitInTime"]
                        if pd.isna(pit_in_value): continue

                        pit_start = pit_in_value.total_seconds()
                        if self.global_start:
                            pit_start -= self.global_start
                    except:
                        continue
                
                pit_end = pit_start + 25.0

                try:
                    next_lap = self.session.laps[
                        (self.session.laps["DriverNumber"].astype(str) == str(driver)) & 
                        (self.session.laps["LapNumber"] == row["LapNumber"] + 1)
                    ]

                    if not next_lap.empty:
                        pit_out_value = next_lap.iloc[0]["PitOutTime"]
                        if not pd.isna(pit_out_value):
                            end = pit_out_value.total_seconds()
                            if self.global_start:
                                end -= self.global_start
                            
                            if end > pit_start:
                                pit_end = end
                except:
                    pass

                windows.append((float(pit_start), float(pit_end)))
            
            self.pit_windows[str(driver)] = windows
    
