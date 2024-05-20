from core.security import create_access_token, decode_access_token


def test_access_token():
    email = "test_email@mail.com"

    for aim in ["login", "reset_password", "verify_email"]:
        for email_status in [True, False]:
            jwt_token = create_access_token(
                data={"email": email, "aim": aim}, email=email_status
            )
            email_decoded, aim_decoded = decode_access_token(jwt_token)

            assert (
                email == email_decoded
            ), f"Email ({email}) and decoded email ({email_decoded}) are not equal"
            assert (
                aim == aim_decoded
            ), f"Aim ({aim}) and decoded aim ({aim_decoded}) are not equal"
