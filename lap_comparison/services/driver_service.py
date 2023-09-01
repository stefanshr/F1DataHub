import fastf1 as ff1


def fetch_drivers(year, venue, session_type):
    ff1.Cache.enable_cache("cache")

    event = ff1.get_event(year=year, gp=venue)
    session = event.get_session(session_type)
    session.load(laps=False, telemetry=False, weather=False, messages=False)
    driver_numbers = session.drivers

    drivers = []

    for driver_number in driver_numbers:
        driver = session.get_driver(driver_number)
        driver_info = {
            'driverNumber': driver_number,
            'lastName': driver.LastName,
            'firstName': driver.FirstName,
            'headshotUrl': driver.HeadshotUrl,
            'abbreviation': driver.Abbreviation,
            'countryCode': driver.CountryCode,
            'teamName': driver.TeamName,
            'teamColor': '#' + driver.TeamColor
        }
        drivers.append(driver_info)

    return drivers
