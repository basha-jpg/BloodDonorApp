import json
import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Serve static files (index.html, admin.html) from this folder
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)
app.url_map.strict_slashes = False  # accept both /path and /path/

DONOR_DATA = []
DATA_FILE = 'donors.json'
AVAILABLE_KEY = 'AVAILABLE'  # used for comparisons in upper-case


# ---------- Load & Save Helpers ----------

def load_donor_data():
    """Load donors.json into DONOR_DATA."""
    global DONOR_DATA
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, DATA_FILE)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if content.startswith('\ufeff'):  # strip BOM if present
                content = content.lstrip('\ufeff')
            DONOR_DATA = json.loads(content)

        print(f"✅ Loaded {len(DONOR_DATA)} donors from {DATA_FILE}")

    except FileNotFoundError:
        print(f"⚠️ {DATA_FILE} not found, starting with empty list.")
        DONOR_DATA = []
    except json.JSONDecodeError:
        print(f"⚠️ JSON decode error in {DATA_FILE}, starting empty.")
        DONOR_DATA = []


def save_donor_data():
    """Persist DONOR_DATA back to donors.json."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(current_dir, DATA_FILE)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(DONOR_DATA, f, indent=4)


def next_id():
    """Return the next integer id."""
    return max((int(d.get('id', 0)) for d in DONOR_DATA), default=0) + 1


# ---------- Static Routes ----------

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')


@app.route('/admin')
def serve_admin():
    return send_from_directory('.', 'admin.html')


# ---------- API: Status ----------

@app.route('/api/status')
def status():
    return jsonify({
        "app_version": "1.4",
        "donor_count": len(DONOR_DATA),
        "status": "Server is running ✅"
    })


# ---------- API: Search Donors ----------

@app.route('/api/donors/search', methods=['GET'])
def search_donors():
    """
    - No params -> return ALL donors (admin page).
    - blood_group=X -> return donors with that group AND Availability_Status == 'Available' (public).
    - Optional name=... -> substring, case-insensitive (works with or without blood_group).
    """
    blood_group_input = request.args.get('blood_group')
    name_input = request.args.get('name')

    # No filters: return all (used by admin)
    if not blood_group_input and not name_input:
        return jsonify(DONOR_DATA)

    bg_key = (blood_group_input or '').strip().upper()
    name_key = (name_input or '').strip().upper()

    results = []
    for donor in DONOR_DATA:
        donor_blood = (donor.get('Blood_Group') or '').strip().upper()
        donor_name = (donor.get('Name') or '').strip().upper()
        avail = (donor.get('Availability_Status') or 'Unavailable').strip().upper()

        # If blood group is provided, enforce AVAILABLE (public search behavior)
        if bg_key:
            if donor_blood != bg_key:
                continue
            if avail != AVAILABLE_KEY:
                continue

        # If name filter present, do case-insensitive substring match
        if name_key and name_key not in donor_name:
            continue

        results.append(donor)

    return jsonify(results)


# ---------- API: Create Donor ----------

@app.route('/api/donors', methods=['POST', 'OPTIONS'])
@app.route('/api/donors/register', methods=['POST', 'OPTIONS'])
def create_donor():
    # Handle preflight for CORS
    if request.method == 'OPTIONS':
        return ('', 204)

    data = request.get_json(silent=True) or request.form.to_dict()

    # Required fields (match your frontend)
    required = ['Name', 'Phone_Number', 'Blood_Group']
    missing = [f for f in required if not (data.get(f))]
    if missing:
        return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

    # Accept either City or Address from clients; always store as Address
    address = (data.get('Address') or data.get('City') or '').strip()

    donor = {
        "id": next_id(),
        "Name": str(data['Name']).strip(),
        "Phone_Number": str(data['Phone_Number']).strip(),
        # normalize blood group in storage as uppercase like your JSON uses (A+, AB+ ...)
        "Blood_Group": str(data['Blood_Group']).strip().upper(),
        # keep pretty case for display; searching upper-cases internally
        "Availability_Status": (data.get('Availability_Status') or 'Available').strip().capitalize(),
        "Address": address
    }

    DONOR_DATA.append(donor)
    save_donor_data()

    return jsonify(donor), 201


# ---------- API: Update Availability ----------

@app.route('/api/donors/update_status', methods=['POST'])
def update_status():
    try:
        data = request.get_json()
        donor_id = data.get('id')
        new_status = data.get('new_status')

        if not donor_id or not new_status:
            return jsonify({"error": "Missing 'id' or 'new_status'."}), 400

        for donor in DONOR_DATA:
            if str(donor.get('id')) == str(donor_id):
                donor['Availability_Status'] = str(new_status).strip().capitalize()
                save_donor_data()
                return jsonify({"success": True, "message": "Status updated."})

        return jsonify({"error": "Donor not found."}), 404

    except Exception as e:
        print("Update error:", e)
        return jsonify({"error": "Internal server error."}), 500


# ---------- Main ----------

if __name__ == '__main__':
    load_donor_data()
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
else:
    load_donor_data()
