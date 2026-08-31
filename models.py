from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Time

db = SQLAlchemy()


class Business(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    # owner_cognito_sub = db.Column(
    #     db.String(255)
    # )

    business_name = db.Column(db.String(200))
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100))
    description = db.Column(db.Text)
    # Opening Hours

    mon_thu_open = db.Column(db.Time, nullable=True)
    mon_thu_close = db.Column(db.Time, nullable=True)

    fri_open = db.Column(db.Time, nullable=True)
    fri_close = db.Column(db.Time, nullable=True)

    sat_open = db.Column(db.Time, nullable=True)
    sat_close = db.Column(db.Time, nullable=True)

    sun_open = db.Column(db.Time, nullable=True)
    sun_close = db.Column(db.Time, nullable=True)

    holiday_open = db.Column(db.Time, nullable=True)
    holiday_close = db.Column(db.Time, nullable=True)

    website = db.Column(db.String(255))

    phone = db.Column(db.String(20))
    whatsapp = db.Column(db.String(20))
    email = db.Column(db.String(120))
    address = db.Column(db.String(255))

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    show_address = db.Column(db.Boolean,default=False)
    show_whatsapp = db.Column(db.Boolean,default=False)
    show_phone = db.Column(db.Boolean,default=True)

    status = db.Column(
        db.String(20),
        default="pending"
    )

    views = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    last_viewed = db.Column(
        db.DateTime,
        nullable=True
    )

    images = db.relationship(
        "BusinessImage",
        backref="business",
        lazy=True,
        cascade="all, delete-orphan"
    )

# class BusinessDocument(db.Model):

#     id = db.Column(db.Integer, primary_key=True)

#     business_id = db.Column(
#         db.Integer,
#         db.ForeignKey("business.id"),
#         nullable=False
#     )

#     file_path = db.Column(db.String(500))


class BusinessImage(db.Model):
    __tablename__ = "business_images"

    id = db.Column(db.Integer, primary_key=True)

    business_id = db.Column(
        db.Integer,
        db.ForeignKey("business.id"),
        nullable=False
    )

    image_url = db.Column(
        db.String(500),
        nullable=False
    )

