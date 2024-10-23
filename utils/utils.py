from pyrogram.types import User


def is_valid_user(user: User):
    if not isinstance(user, User):
        raise TypeError
    if (
            user.is_bot or user.is_fake or
            user.is_deleted or user.is_contact or
            user.is_restricted or user.is_scam
    ):
        raise ValueError
    return True


def main():
    pass


if __name__ == "__main__":
    main()
