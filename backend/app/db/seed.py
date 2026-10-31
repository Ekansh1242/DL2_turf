from app.db.session import SessionLocal, engine
from app.domain.models.models import Base, University, Campus, Resource, SportType, EquipmentCatalog, User, UserRole

SPORT_DISPLAY_NAMES = {
    SportType.football: "Football Ground",
    SportType.cricket: "Cricket Ground",
    SportType.basketball: "Basketball Court",
    SportType.badminton: "Badminton Court",
    SportType.pickleball: "Pickleball Court",
    SportType.table_tennis: "Table Tennis Room",
    SportType.lawn_tennis: "Lawn Tennis Court",
    SportType.chess: "Chess Room",
}

EQUIPMENT_CATALOG = {
    SportType.football: [("Football", 5)],
    SportType.cricket: [("Bat", 6), ("Ball", 10), ("Stumps Set", 3), ("Helmet", 6), ("Knee Pads", 6)],
    SportType.basketball: [("Basketball", 5)],
    SportType.badminton: [("Racket", 10), ("Shuttlecock", 30)],
    SportType.pickleball: [("Paddle", 8), ("Ball", 15)],
    SportType.table_tennis: [("Racket", 8), ("Ball", 20)],
    SportType.lawn_tennis: [("Racket", 6), ("Ball", 20)],
    SportType.chess: [("Chess Set", 10)],
}


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        uni = db.query(University).first()
        if uni is None:
            uni = University(name="Shri Ramdeobaba College of Engineering & Management")
            db.add(uni)
            db.flush()
        campus = db.query(Campus).first()
        if campus is None:
            campus = Campus(university_id=uni.id, name="RCOEM Main Campus", timezone="Asia/Kolkata")
            db.add(campus)
            db.flush()
        for sport, display_name in SPORT_DISPLAY_NAMES.items():
            existing = db.query(Resource).filter(Resource.type == sport).first()
            if existing is None:
                db.add(Resource(campus_id=campus.id, name=display_name, type=sport))
        db.flush()
        for sport, items in EQUIPMENT_CATALOG.items():
            for name, qty in items:
                existing = db.query(EquipmentCatalog).filter(EquipmentCatalog.sport == sport, EquipmentCatalog.name == name).first()
                if existing is None:
                    db.add(EquipmentCatalog(sport=sport, name=name, quantity_total=qty, quantity_available=qty))

        # Demo staff/admin login for the sports department -- teachers use
        # the same login flow as students, just with role=admin.
        staff = db.query(User).filter(User.email == "sports.office@rknec.edu").first()
        if staff is None:
            db.add(User(
                campus_id=campus.id, name="Sports Department", email="sports.office@rknec.edu",
                role=UserRole.admin, department="Sports",
            ))

        db.commit()
        print("Seed complete. Staff login: sports.office@rknec.edu")
    finally:
        db.close()


if __name__ == "__main__":
    run()
