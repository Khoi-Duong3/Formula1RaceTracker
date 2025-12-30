import fastf1

session = fastf1.get_session(2025, "Brazil", "R")
session.load(telemetry=True, weather=False, laps=True)
laps = session.laps


print(session.drivers)

