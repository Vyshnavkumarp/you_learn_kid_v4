from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash  # Add this import

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password = db.Column('password', db.String(200), nullable=False)  # Note the rename of the db column
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80))
    age = db.Column(db.Integer)
    parent_email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    login_streak = db.Column(db.Integer, default=1)
    level = db.Column(db.Integer, default=1)
    total_xp = db.Column(db.Integer, default=0)
    
    # Add other model relationships here
    activities = db.relationship('Activity', back_populates='user')
    achievements = db.relationship('UserAchievement', back_populates='user')

    def __init__(self, **kwargs):
        self.password_hash = kwargs.pop('password', None)
        super(User, self).__init__(**kwargs)

    @property
    def password(self):
        """Prevent password from being accessed"""
        raise AttributeError('Password is not a readable attribute')

    @password.setter
    def password(self, password):
        """Set password to a hashed password"""
        self._password = generate_password_hash(password, method='pbkdf2:sha256')

    def verify_password(self, password):
        """Check if the provided password matches the hash"""
        return check_password_hash(self._password, password)

    def add_xp(self, points):
        """Add XP points and handle level ups"""
        self.total_xp += points
        
        # Check for level up
        new_level = 1 + (self.total_xp // 100)  # Simple formula: level = 1 + (XP / 100)
        if new_level > self.level:
            self.level = new_level
            
        db.session.commit()
        return points

    def to_dict(self):
        """Convert user object to dictionary for API responses."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'age': self.age,
            'login_streak': self.login_streak,
            'level': self.level,
            'total_xp': self.total_xp
        }

class QuizAttempt(db.Model):
    __tablename__ = 'quiz_attempts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'topic': self.topic,
            'score': self.score,
            'max_score': self.max_score,
            'created_at': self.created_at.isoformat()
        }

class Achievement(db.Model):
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(50), nullable=False)
    points = db.Column(db.Integer, default=0)
    # Add the missing category column
    category = db.Column(db.String(50), nullable=True)
    
    # Many users can have many achievements
    users = db.relationship('UserAchievement', back_populates='achievement')

class UserAchievement(db.Model):
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Define relationships
    user = db.relationship('User', back_populates='achievements')
    achievement = db.relationship('Achievement', back_populates='users')
    
    # Ensure a user can't earn the same achievement twice
    __table_args__ = (db.UniqueConstraint('user_id', 'achievement_id'),)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'achievement_id': self.achievement_id,
            'achievement_name': self.achievement.name if self.achievement else None,
            'earned_at': self.earned_at.isoformat()
        }

class LearningSession(db.Model):
    __tablename__ = 'learning_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    xp_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'topic': self.topic,
            'duration_minutes': self.duration_minutes,
            'xp_earned': self.xp_earned,
            'created_at': self.created_at.isoformat()
        }

# Fix the Activity model by renaming the reserved 'metadata' column
class Activity(db.Model):
    __tablename__ = 'activities'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # e.g., 'chat', 'quiz', etc.
    xp_earned = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Rename "metadata" to "activity_metadata" since "metadata" is reserved
    content = db.Column(db.Text, nullable=True)  # For storing chat messages, quiz answers, etc.
    activity_metadata = db.Column(db.JSON, nullable=True)  # For additional data
    
    user = db.relationship('User', back_populates='activities')
