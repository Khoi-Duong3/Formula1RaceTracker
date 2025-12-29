import fastf1

session = fastf1.get_session(2024, "Baku", "R")
session.load(telemetry=True, weather=False, laps=True)
laps = session.laps
lando = laps[session.laps["DriverNumber"] == "4"]

print(lando["Compound"])

