import json
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Initialize Flask, telling it to serve static files from the root directory '.'
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DONOR_DATA = []
DATA_FILE = 'donors.json'
AVAILABLE_KEY = 'AVAILABLE'

def load_donor_data():
    """Loads donor data from the JSON file into the global DONOR_DATA list."""
    global DONOR_DATA
    try:
        # Use a path relative to this file (app.py)
        # This is robust for both local (python app.py) and production (gunicorn)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_FILE)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Handle potential BOM (Byte Order Mark) at the start of the file
            if content.startswith('\ufeff'):
                content = content.lstrip('\ufeff')
            DONOR_DATA = json.loads(content)
        
        # This will now print to the Render logs, not your local terminal
        print(f"Successfully loaded {len(DONOR_DATA)} donor records from {DATA_FILE}.")

    except FileNotFoundError:
        print(f"Error: {DATA_FILE} not found at {file_path}. Please ensure the file is in the same directory.")
        DONOR_DATA = []
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {DATA_FILE}. Check file formatting.")
        DONOR_DATA = []

# --- Static File Routes ---

@app.route('/')
def serve_index():
    """Serves the main index.html file as the homepage."""
    # send_from_directory will look in the 'static_folder' (which we set to '.')
    return send_from_directory('.', 'index.html')

@app.route('/admin')
def serve_admin():
    """Serves the admin.html file."""
    # We explicitly define this route so users can navigate to /admin
    return send_from_directory('.', 'admin.html')

# --- API Routes ---

@app.route('/api/status')
def home():
    """A status endpoint to check if the server is running and data is loaded."""
    return jsonify({
        "app_version": "1.2", # Updated version
        "donor_count": len(DONOR_DATA),
        "status": "Server is running."
    })

@app.route('/api/donors/search', methods=['GET'])
def search_donors():
    """
    Handles searching for donors.
    - If 'blood_group' param exists, filters by it (for index.html).
    - If no param exists, returns all donors (for admin.html).
    """
    blood_group_input = request.args.get('blood_group')

    # This logic now handles both index.html (with blood_group) and admin.html (no blood_group)
    if not blood_group_input:
        # No blood group provided, return all donors (for Admin panel)
        return jsonify(DONOR_DATA)

    # --- Filter by Blood Group (for Public Search) ---
    search_key_blood = blood_group_input.strip().upper()
    
    results = []
    for donor in DONOR_DATA:
        # Clean data from file on-the-fly for robust matching
        donor_blood_group = donor.get('Blood_Group', '').strip().upper()
        availability_status = donor.get('Availability_Status', 'Unavailable').strip().upper()
        
        # Check both conditions
        if donor_blood_group == search_key_blood and availability_status == AVAILABLE_KEY:
            results.append(donor)

    return jsonify(results)

@app.route('/api/donors/update_status', methods=['POST'])
def update_status():
    """Handles updating a donor's availability status."""
    global DONOR_DATA
    try:
        data = request.get_json()
        donor_id = data.get('id')
        new_status = data.get('new_status')

        if not donor_id or not new_status:
            return jsonify({"error": "Missing 'id' or 'new_status'."}), 400

        donor_found = False
        for i, donor in enumerate(DONOR_DATA):
            # Compare ID as string to be safe
            if str(donor.get('id')) == str(donor_id):
                DONOR_DATA[i]['Availability_Status'] = new_status
                donor_found = True
                break
        
        if not donor_found:
            return jsonify({"error": "Donor ID not found."}), 404

        # Save the updated data back to the file
        # This makes the change persistent on the server
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_FILE)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(DONOR_DATA, f, indent=4)
            
        return jsonify({"success": True, "message": "Donor status updated."})

    except Exception as e:
        print(f"Error updating status: {e}")
        return jsonify({"error": "Internal server error."}), 500

# --- Main execution ---
if __name__ == '__main__':
    # This block runs when you execute `python app.py` locally
    load_donor_data()
    # Use environment variable for port, default to 5000 for local dev
    port = int(os.environ.get('PORT', 5000))
    # Run on 0.0.0.0 to be accessible on your local network
    app.run(debug=True, host='0.0.0.0', port=port)
else:
    # This block runs when Gunicorn starts the app on Render
    # Gunicorn handles the server, so we just need to load the data
    load_donor_data()