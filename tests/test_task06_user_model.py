def test_user_model_table_name():
    from app.database import UserModel
    assert UserModel.__tablename__ == "users"


def test_user_model_columns():
    from app.database import UserModel
    columns = {c.name for c in UserModel.__table__.columns}
    assert {"id", "username", "password_hash", "created_at"} <= columns


def test_username_is_unique():
    from app.database import UserModel
    col = UserModel.__table__.c.username
    assert col.unique is True
