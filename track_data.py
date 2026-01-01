import fastf1

session = fastf1.get_session(2025, "Brazil", "R")
session.load(telemetry=True, weather=False, laps=True)
pit_laps = session.laps[~session.laps["PitInTime"].isna()]


print(f"{pit_laps["DriverNumber"]} {pit_laps["PitInTime"]}")

