from core.hashing import Hasher


def test_hasher():
    for password in ["irndgokmfl", "rhtsdjglks", "534kj4bi3ukt4ernjg"]:
        hashed_password = Hasher.get_password_hash(password)
        assert Hasher.verify_password(
            password, hashed_password
        ), f"Password ({password}) and hashed password ({hashed_password}) are not verified"
