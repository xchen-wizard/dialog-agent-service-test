from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_: str, name: str, email: str):
        self.id = id_
        self.name = name
        self.email = email
        
    def is_authenticated(self):
        return True
