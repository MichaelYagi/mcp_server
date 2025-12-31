CITY_TIMEZONES = {
    # Canada
    ("Surrey", "Canada"): "America/Vancouver",
    ("Vancouver", "Canada"): "America/Vancouver",
    ("Burnaby", "Canada"): "America/Vancouver",
    ("Richmond", "Canada"): "America/Vancouver",
    ("Calgary", "Canada"): "America/Edmonton",
    ("Edmonton", "Canada"): "America/Edmonton",
    ("Winnipeg", "Canada"): "America/Winnipeg",
    ("Toronto", "Canada"): "America/Toronto",
    ("Ottawa", "Canada"): "America/Toronto",
    ("Montreal", "Canada"): "America/Toronto",
    ("Quebec City", "Canada"): "America/Toronto",

    # USA
    ("New York", "USA"): "America/New_York",
    ("Boston", "USA"): "America/New_York",
    ("Washington", "USA"): "America/New_York",
    ("Miami", "USA"): "America/New_York",
    ("Chicago", "USA"): "America/Chicago",
    ("Houston", "USA"): "America/Chicago",
    ("Dallas", "USA"): "America/Chicago",
    ("Denver", "USA"): "America/Denver",
    ("Phoenix", "USA"): "America/Phoenix",
    ("Los Angeles", "USA"): "America/Los_Angeles",
    ("San Francisco", "USA"): "America/Los_Angeles",
    ("Seattle", "USA"): "America/Los_Angeles",

    # UK
    ("London", "UK"): "Europe/London",
    ("Manchester", "UK"): "Europe/London",
    ("Birmingham", "UK"): "Europe/London",
    ("Edinburgh", "UK"): "Europe/London",

    # Europe
    ("Paris", "France"): "Europe/Paris",
    ("Marseille", "France"): "Europe/Paris",
    ("Berlin", "Germany"): "Europe/Berlin",
    ("Munich", "Germany"): "Europe/Berlin",
    ("Rome", "Italy"): "Europe/Rome",
    ("Milan", "Italy"): "Europe/Rome",
    ("Madrid", "Spain"): "Europe/Madrid",
    ("Barcelona", "Spain"): "Europe/Madrid",
    ("Amsterdam", "Netherlands"): "Europe/Amsterdam",
    ("Brussels", "Belgium"): "Europe/Brussels",
    ("Zurich", "Switzerland"): "Europe/Zurich",
    ("Vienna", "Austria"): "Europe/Vienna",
    ("Stockholm", "Sweden"): "Europe/Stockholm",
    ("Oslo", "Norway"): "Europe/Oslo",
    ("Copenhagen", "Denmark"): "Europe/Copenhagen",
    ("Warsaw", "Poland"): "Europe/Warsaw",
    ("Prague", "Czech Republic"): "Europe/Prague",
    ("Lisbon", "Portugal"): "Europe/Lisbon",
    ("Athens", "Greece"): "Europe/Athens",

    # Japan
    ("Tokyo", "Japan"): "Asia/Tokyo",
    ("Yokohama", "Japan"): "Asia/Tokyo",
    ("Osaka", "Japan"): "Asia/Tokyo",
    ("Nagoya", "Japan"): "Asia/Tokyo",
    ("Sapporo", "Japan"): "Asia/Tokyo",
    ("Fukuoka", "Japan"): "Asia/Tokyo",
    ("Chigasaki", "Japan"): "Asia/Tokyo",

    # East Asia
    ("Seoul", "South Korea"): "Asia/Seoul",
    ("Busan", "South Korea"): "Asia/Seoul",
    ("Shanghai", "China"): "Asia/Shanghai",
    ("Beijing", "China"): "Asia/Shanghai",
    ("Shenzhen", "China"): "Asia/Shanghai",
    ("Taipei", "Taiwan"): "Asia/Taipei",
    ("Hong Kong", "Hong Kong"): "Asia/Hong_Kong",

    # Southeast Asia
    ("Singapore", "Singapore"): "Asia/Singapore",
    ("Kuala Lumpur", "Malaysia"): "Asia/Kuala_Lumpur",
    ("Bangkok", "Thailand"): "Asia/Bangkok",
    ("Ho Chi Minh City", "Vietnam"): "Asia/Ho_Chi_Minh",
    ("Hanoi", "Vietnam"): "Asia/Bangkok",
    ("Manila", "Philippines"): "Asia/Manila",
    ("Jakarta", "Indonesia"): "Asia/Jakarta",

    # South Asia
    ("Delhi", "India"): "Asia/Kolkata",
    ("Mumbai", "India"): "Asia/Kolkata",
    ("Bangalore", "India"): "Asia/Kolkata",
    ("Karachi", "Pakistan"): "Asia/Karachi",
    ("Dhaka", "Bangladesh"): "Asia/Dhaka",

    # Middle East
    ("Dubai", "UAE"): "Asia/Dubai",
    ("Abu Dhabi", "UAE"): "Asia/Dubai",
    ("Riyadh", "Saudi Arabia"): "Asia/Riyadh",
    ("Doha", "Qatar"): "Asia/Qatar",
    ("Kuwait City", "Kuwait"): "Asia/Kuwait",
    ("Jerusalem", "Israel"): "Asia/Jerusalem",

    # Africa
    ("Johannesburg", "South Africa"): "Africa/Johannesburg",
    ("Cape Town", "South Africa"): "Africa/Johannesburg",
    ("Cairo", "Egypt"): "Africa/Cairo",
    ("Lagos", "Nigeria"): "Africa/Lagos",
    ("Nairobi", "Kenya"): "Africa/Nairobi",
    ("Casablanca", "Morocco"): "Africa/Casablanca",

    # Oceania
    ("Sydney", "Australia"): "Australia/Sydney",
    ("Melbourne", "Australia"): "Australia/Melbourne",
    ("Brisbane", "Australia"): "Australia/Brisbane",
    ("Perth", "Australia"): "Australia/Perth",
    ("Auckland", "New Zealand"): "Pacific/Auckland",
    ("Wellington", "New Zealand"): "Pacific/Auckland",
}

COUNTRY_TIMEZONES = {
    # North America
    "Canada": "America/Toronto",          # default; west coast cities override via CITY_TIMEZONES
    "USA": "America/New_York",
    "Mexico": "America/Mexico_City",

    # South America
    "Brazil": "America/Sao_Paulo",
    "Argentina": "America/Argentina/Buenos_Aires",
    "Chile": "America/Santiago",
    "Colombia": "America/Bogota",
    "Peru": "America/Lima",

    # Europe
    "UK": "Europe/London",
    "Ireland": "Europe/Dublin",
    "France": "Europe/Paris",
    "Germany": "Europe/Berlin",
    "Spain": "Europe/Madrid",
    "Italy": "Europe/Rome",
    "Netherlands": "Europe/Amsterdam",
    "Belgium": "Europe/Brussels",
    "Sweden": "Europe/Stockholm",
    "Norway": "Europe/Oslo",
    "Finland": "Europe/Helsinki",
    "Denmark": "Europe/Copenhagen",
    "Poland": "Europe/Warsaw",
    "Czech Republic": "Europe/Prague",
    "Austria": "Europe/Vienna",
    "Switzerland": "Europe/Zurich",
    "Portugal": "Europe/Lisbon",
    "Greece": "Europe/Athens",
    "Turkey": "Europe/Istanbul",

    # Middle East
    "Israel": "Asia/Jerusalem",
    "Saudi Arabia": "Asia/Riyadh",
    "UAE": "Asia/Dubai",
    "Qatar": "Asia/Qatar",
    "Kuwait": "Asia/Kuwait",

    # Africa
    "South Africa": "Africa/Johannesburg",
    "Egypt": "Africa/Cairo",
    "Nigeria": "Africa/Lagos",
    "Kenya": "Africa/Nairobi",
    "Morocco": "Africa/Casablanca",

    # Asia
    "Japan": "Asia/Tokyo",
    "South Korea": "Asia/Seoul",
    "China": "Asia/Shanghai",
    "Taiwan": "Asia/Taipei",
    "Hong Kong": "Asia/Hong_Kong",
    "Singapore": "Asia/Singapore",
    "Malaysia": "Asia/Kuala_Lumpur",
    "Thailand": "Asia/Bangkok",
    "Vietnam": "Asia/Ho_Chi_Minh",
    "Philippines": "Asia/Manila",
    "India": "Asia/Kolkata",
    "Pakistan": "Asia/Karachi",
    "Bangladesh": "Asia/Dhaka",
    "Indonesia": "Asia/Jakarta",

    # Oceania
    "Australia": "Australia/Sydney",
    "New Zealand": "Pacific/Auckland",
}

DEFAULT_TZ = "UTC"   # safe fallback