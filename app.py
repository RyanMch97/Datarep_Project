from flask import Flask, render_template, request, jsonify
import mysql.connector
import requests
import http.client
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry

app = Flask(__name__)

# My MySQL creds
mysql_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'datarep_db', #You will need to add your own details here 
}

conn = mysql.connector.connect(**mysql_config)
cursor = conn.cursor()

# Setup the Open-Meteo API client 
# API code got here: https://open-meteo.com/en/docs#hourly=apparent_temperature
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

@app.route('/')
def index():
    return render_template('index.html')

# Route to fetch items
@app.route('/api/items', methods=['GET', 'POST'])
def items():
    if request.method == 'GET':
        cursor.execute('SELECT * FROM items')
        items = cursor.fetchall()
        return jsonify({'items': [{'id': item[0], 'name': item[1]} for item in items]})
    elif request.method == 'POST':
        data = request.json
        cursor.execute('INSERT INTO items (name) VALUES (%s)', (data['name'],))
        conn.commit()
        return jsonify({'message': 'Item added successfully'}), 201

# Route to handle individual items
@app.route('/api/items/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
def item(item_id):
    cursor.execute('SELECT * FROM items WHERE id = %s', (item_id,))
    item = cursor.fetchone()

    if item is None:
        return jsonify({'error': 'Item not found'}), 404

    if request.method == 'GET':
        return jsonify({'id': item[0], 'name': item[1]})
    elif request.method == 'PUT':
        data = request.json
        cursor.execute('UPDATE items SET name = %s WHERE id = %s', (data['name'], item_id))
        conn.commit()
        return jsonify({'message': 'Item updated successfully'})
    elif request.method == 'DELETE':
        cursor.execute('DELETE FROM items WHERE id = %s', (item_id,))
        conn.commit()
        return jsonify({'message': 'Item deleted successfully'})

# Route to fetch categories
@app.route('/api/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'GET':
        cursor.execute('SELECT * FROM categories')
        categories = cursor.fetchall()
        return jsonify({'categories': [{'id': category[0], 'name': category[1]} for category in categories]})
    elif request.method == 'POST':
        data = request.json
        cursor.execute('INSERT INTO categories (name) VALUES (%s)', (data['name'],))
        conn.commit()
        return jsonify({'message': 'Category added successfully'}), 201

# Route to handle individual categories
@app.route('/api/categories/<int:category_id>', methods=['GET', 'PUT', 'DELETE'])
def category(category_id):
    cursor.execute('SELECT * FROM categories WHERE id = %s', (category_id,))
    category = cursor.fetchone()

    if category is None:
        return jsonify({'error': 'Category not found'}), 404

    if request.method == 'GET':
        return jsonify({'id': category[0], 'name': category[1]})
    elif request.method == 'PUT':
        data = request.json
        cursor.execute('UPDATE categories SET name = %s WHERE id = %s', (data['name'], category_id))
        conn.commit()
        return jsonify({'message': 'Category updated successfully'})
    elif request.method == 'DELETE':
        cursor.execute('DELETE FROM categories WHERE id = %s', (category_id,))
        conn.commit()
        return jsonify({'message': 'Category deleted successfully'})

# Route to fetch weather data from the Open-Meteo API
@app.route('/api/weather', methods=['GET'])
def weather():
    try:
        # weather variables are listed here, Galway co-ords right so I can easily see if working
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 53.27,
            "longitude": -9.05,
            "hourly": ["apparent_temperature", "rain"]
        }
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]

        # Process hourly data.
        hourly = response.Hourly()
        hourly_apparent_temperature = hourly.Variables(0).ValuesAsNumpy()
        hourly_rain = hourly.Variables(1).ValuesAsNumpy()

        hourly_data = {"date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s"),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s"),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left"
        )}
        hourly_data["apparent_temperature"] = hourly_apparent_temperature
        hourly_data["rain"] = hourly_rain

        hourly_dataframe = pd.DataFrame(data=hourly_data)

        return jsonify(hourly_dataframe.to_dict(orient='records'))
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
