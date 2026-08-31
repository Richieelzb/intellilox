import os
import requests
from flask import Flask, render_template, request, jsonify
from sqlalchemy import or_
from flask_sqlalchemy import SQLAlchemy
from models import db, Business
from math import radians, sin, cos, sqrt, atan2
from datetime import datetime
from flask import session

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

S3_BUCKET_NAME = os.getenv(
    "S3_BUCKET_NAME"
)

SES_REGION = os.getenv(
    "SES_REGION"
)

app.config["SESSION_COOKIE_DOMAIN"] = ".ecs-sandbox.co.za"
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"postgresql://"
    f"{DB_USER}:"
    f"{DB_PASSWORD}@"
    f"{DB_HOST}:"
    f"{DB_PORT}/"
    f"{DB_NAME}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

# @app.route("/")
# def home():
#  return render_template("index.html")


def distance_km(lat1, lon1, lat2, lon2):

    R = 6371

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


@app.route("/api/business-count")
def business_count():

    lat = request.args.get("lat", type=float)
    lng = request.args.get("lng", type=float)

    if lat is None or lng is None:
        return jsonify({"count": 0})

    businesses = Business.query.filter_by(
        status="approved"
    ).all()

    count = 0

    for business in businesses:

        if business.latitude and business.longitude:

            distance = distance_km(
                lat,
                lng,
                business.latitude,
                business.longitude
            )

            if distance <= 50:
                count += 1

    return jsonify({
        "count": count
    })

@app.route("/")
def home():

    email = session.get("email")

    business = None

    if email:
        business = Business.query.filter_by(
            email=email
        ).first()

    return render_template(
        "index.html",
        email=email
    )

def get_address(lat, lng):
    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?latlng={lat},{lng}"
        f"&key={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data["results"]:
        return data["results"][0]["formatted_address"]

    return "Location not found"

def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in km

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return round(R * c, 1)

@app.template_filter("hours")
def hours_display(value):
    return value.strftime("%H:%M") if value else "Closed"

@app.template_global()
def whatsapp_link(number):
    if not number:
        return None

    number = str(number).strip()

    # Remove common formatting
    number = number.replace(" ", "")
    number = number.replace("-", "")
    number = number.replace("(", "")
    number = number.replace(")", "")

    # South African local format: 0821234567 → 27821234567
    if number.startswith("0"):
        number = "27" + number[1:]

    # International format: +27821234567 → 27821234567
    elif number.startswith("+"):
        number = number[1:]

    return "https://wa.me/" + number

@app.route("/search")
def search():
    query = request.args.get("query")
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")
    try:
        url = (
            "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            f"?keyword={query}"
            f"&location={latitude},{longitude}"
            "&radius=10000"
            f"&key={API_KEY}"
        )

        response = requests.get(url)
        data = response.json()

        results = []

        for place in data.get("results", []):

            place_lat = place["geometry"]["location"]["lat"]
            place_lng = place["geometry"]["location"]["lng"]

            distance = calculate_distance(float(latitude), float(longitude), place_lat, place_lng)

            results.append({
                "name": place.get("name"),
                "address": place.get("formatted_address") or place.get("vicinity"),
                "rating": place.get("rating", "N/A"),
                "distance": distance,
                "lat": place_lat,    
                "lng": place_lng
            })
        results.sort(key=lambda x: x["distance"])
    except Exception as e:
                print(e)
                results = []

    return render_template(
        "results.html",
        query=query,
        results=results
    )

@app.route("/location")
def location():
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?latlng={lat},{lng}"
        f"&key={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data["results"]:
        address = data["results"][0]["formatted_address"]
    else:
        address = "Location not found"

    return {"address": address}

@app.route("/business-search")
def business_search():

    query = request.args.get("query", "").strip()
    latitude = request.args.get("latitude")
    longitude = request.args.get("longitude")

    businesses = []

    # Force location
    if not latitude or not longitude:
        return render_template(
            "business_results.html",
            businesses=[],
            query=query,
            error="Location access is required."
        )

    user_lat = float(latitude)
    user_lng = float(longitude)

    keywords = query.split()

    conditions = []

    for keyword in keywords:
        search_term = f"%{keyword}%"

        conditions.extend([
            Business.business_name.ilike(search_term),
            Business.category.ilike(search_term),
            Business.subcategory.ilike(search_term),
            Business.description.ilike(search_term),
            Business.address.ilike(search_term)
        ])

    matching_businesses = Business.query.filter(
        Business.status == "approved",
        or_(*conditions),
        Business.latitude.between(user_lat - 0.5, user_lat + 0.5),
        Business.longitude.between(user_lng - 0.5, user_lng + 0.5)
    ).all()

    for business in matching_businesses:

        if not business.latitude or not business.longitude:
            continue

        distance = calculate_distance(
            user_lat,
            user_lng,
            business.latitude,
            business.longitude
        )

        if distance <= 50:
            business.distance = distance
            businesses.append(business)
    # Closest first
    businesses.sort(key=lambda x: x.distance)

    return render_template(
        "business_results.html",
        businesses=businesses,
        query=query
    )

@app.route(
    "/business-view/<int:business_id>",
    methods=["POST"]
)
@app.route("/business-view/<int:business_id>", methods=["POST"])
def count_business_view(business_id):

    business = Business.query.get_or_404(business_id)

    business.views += 1
    business.last_viewed = datetime.utcnow()

    db.session.commit()

    return {"success": True}, 200

def get_coordinates(address):

    url = (
        "https://maps.googleapis.com/maps/api/geocode/json"
        f"?address={address}"
        f"&key={API_KEY}"
    )

    response = requests.get(url)
    data = response.json()

    if data["results"]:

        location = (
            data["results"][0]
            ["geometry"]
            ["location"]
        )

        return (
            location["lat"],
            location["lng"]
        )

    return None, None

@app.route("/health")
def health():
   return {"status": "healthy"}, 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
