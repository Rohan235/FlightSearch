import json
from datetime import datetime
from flask import Flask, request, render_template, jsonify

app = Flask(__name__)

# Function to format arrival time
def format_arrival_time(arrival_time):
    dt = datetime.fromisoformat(arrival_time)
    return dt.strftime("%I:%M %p"), dt

# Function to format departure time
def format_departure_time(departure_time):
    dt = datetime.fromisoformat(departure_time)
    return dt.strftime("%I:%M %p"), dt

# Function to format duration
def format_duration(duration):
    hours, minutes = divmod(duration, 60)
    return f"{hours}h {minutes}min"

# Function to filter and sort flights by departure time range and fare
def filter_and_sort_flights(flights, start_hour, end_hour):
    filtered_flights = [
        flight for flight in flights.values() if start_hour <= flight['departure_dt'].hour < end_hour
    ]
    return sorted(filtered_flights, key=lambda x: (x['total_fare'], x['departure_dt']))

# Function to process the uploaded file
def process_file(file_content):
    data_json = json.loads(file_content)
    unique_flights = {}

    # Extract the flight information
    for trip_info in data_json.get('payload', {}).get('searchResult', {}).get('tripInfos', {}).get('ONWARD', []):
        for segment_info in trip_info.get('sI', []):
            flight_details = segment_info.get('fD', {})
            flight_number = flight_details.get('fN')
            airline_name = flight_details.get('aI', {}).get('name')
            arrival_time = segment_info.get('at')
            departure_time = segment_info.get('dt')
            duration = segment_info.get('duration')
            formatted_arrival_time, arrival_dt = format_arrival_time(arrival_time)
            formatted_departure_time, departure_dt = format_departure_time(departure_time)
            formatted_duration = format_duration(duration)
            fare_types = segment_info.get('priceInfoList', [])

            for fare in fare_types:
                fare_type = fare.get('fareIdentifier')
                if fare_type == 'PUBLISHED':
                    total_fare = next(
                        (
                            price_info.get('fd', {}).get('ADULT', {}).get('fC', {}).get('TF', 0)
                            for price_info in trip_info.get('totalPriceList', [])
                            if price_info.get('fareIdentifier') == 'PUBLISHED'
                        ),
                        0
                    )
                    if flight_number not in unique_flights or unique_flights[flight_number]['total_fare'] > total_fare:
                        unique_flights[flight_number] = {
                            'flight_number': flight_number,
                            'airline_name': airline_name,
                            'total_fare': total_fare,
                            'arrival_time': formatted_arrival_time,
                            'arrival_dt': arrival_dt,
                            'departure_time': formatted_departure_time,
                            'departure_dt': departure_dt,
                            'duration': formatted_duration,
                            'fare_type': fare_type
                        }

    # Filter and sort flights into four lists
    morning_flights = filter_and_sort_flights(unique_flights, 6, 12)
    afternoon_flights = filter_and_sort_flights(unique_flights, 12, 18)
    evening_flights = filter_and_sort_flights(unique_flights, 18, 24)
    night_flights = filter_and_sort_flights(unique_flights, 0, 6)

    total_flights = len(morning_flights) + len(afternoon_flights) + len(evening_flights) + len(night_flights)

    return {
        'morning_flights': morning_flights,
        'morning_flights_count': len(morning_flights),
        'afternoon_flights': afternoon_flights,
        'afternoon_flights_count': len(afternoon_flights),
        'evening_flights': evening_flights,
        'evening_flights_count': len(evening_flights),
        'night_flights': night_flights,
        'night_flights_count': len(night_flights),
        'total_flights': total_flights
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file:
        content = file.read().decode('utf-8')
        result = process_file(content)
        return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
