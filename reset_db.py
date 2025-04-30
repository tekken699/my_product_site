from app import app, db  # Убедитесь, что вы правильно импортируете app и db

with app.app_context():
    db.drop_all()
    db.create_all()
    print("База данных успешно пересоздана.")
