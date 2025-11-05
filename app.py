
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

DONOR_DATA = []
DATA_FILE = 'donors.json'
AVAILABLE_KEY = 'AVAILABLE'

def load_donor_data():
    global DONOR_DATA
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_FILE)
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
            if content.startswith('\ufeff'):
                content = content.lstrip('\ufeff')
            DONOR_DATA = json.loads(content)
        
        print(f"Successfully loaded {len(DONOR_DATA)} donor records from {DATA_FILE}.")
    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found. Please ensure the file is in the same directory.")
        DONOR_DATA = []
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {DATA_FILE}. Check file formatting.")
        DONOR_DATA = []

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "app_version": "1.1",
        "donor_count": len(DONOR_DATA),
        "status": "Server is running."
    })

@app.route('/api/donors/search', methods=['GET'])
def search_donors():
    blood_group_input = request.args.get('blood_group')

    # === THIS IS THE FIX ===
    # If no blood group is provided, return all donors (for Admin Panel)
    if not blood_group_input:
        return jsonify(DONOR_DATA) 
    # === END OF FIX ===

    search_key_blood = blood_group_input.strip().upper()

    results = []
    for donor in DONOR_DATA:
        donor_blood_group = donor.get('Blood_Group', '').strip().upper()
        availability_status = donor.get('Availability_Status', 'Unavailable').strip().upper()
        
        if donor_blood_group == search_key_blood and availability_status == AVAILABLE_KEY:
            results.append(donor)

    return jsonify(results)

@app.route('/api/donors/update_status', methods=['POST'])
def update_donor_status():
    global DONOR_DATA
    data = request.get_json()
    
    donor_id_str = data.get('id')
    new_status = data.get('new_status')

    if not donor_id_str or not new_status:
        return jsonify({"error": "Missing 'id' or 'new_status'."}), 400

    try:
        donor_id = int(donor_id_str)
    except ValueError:
        return jsonify({"error": "Invalid 'id' format."}), 400

    updated_donor = None
    found = False
    
    for donor in DONOR_DATA:
        if donor.get('id') == donor_id:
            donor['Availability_Status'] = new_status
            updated_donor = donor
            found = True
            break
    
    if not found:
        return jsonify({"error": "Donor not found."}), 404

    # Save the updated data back to the JSON file
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_FILE)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(DONOR_DATA, f, indent=4)
        print(f"Successfully updated donor {donor_id} and saved to {DATA_FILE}.")
    except Exception as e:
        print(f"Error saving data to {DATA_FILE}: {e}")
        return jsonify({"error": "Failed to save updated data."}), 500

    return jsonify(updated_donor)

if __name__ == '__main__':
    load_donor_data()
    app.run(debug=True)