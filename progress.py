from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, QuizAttempt, Achievement, UserAchievement, LearningSession
from datetime import datetime, timedelta

progress = Blueprint('progress', __name__)

@progress.route('/stats', methods=['GET'])
@login_required
def get_stats():
    """Get user's learning statistics"""
    try:
        # Get recent quiz attempts
        recent_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id)\
            .order_by(QuizAttempt.created_at.desc())\
            .limit(5)\
            .all()
        
        # Calculate average score
        all_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id).all()
        avg_score = sum(q.score / q.max_score * 100 for q in all_quizzes) / len(all_quizzes) if all_quizzes else 0
        
        # Get total learning time
        learning_sessions = LearningSession.query.filter_by(user_id=current_user.id).all()
        total_time = sum(session.duration for session in learning_sessions if session.duration)
        
        # Get achievements
        achievements = UserAchievement.query.filter_by(user_id=current_user.id)\
            .order_by(UserAchievement.earned_at.desc())\
            .all()
        
        return jsonify({
            'level': current_user.level,
            'total_xp': current_user.total_xp,
            'login_streak': current_user.login_streak,
            'quiz_stats': {
                'total_quizzes': len(all_quizzes),
                'average_score': round(avg_score, 2),
                'recent_quizzes': [q.to_dict() for q in recent_quizzes]
            },
            'learning_time': {
                'total_seconds': total_time,
                'hours': total_time // 3600,
                'minutes': (total_time % 3600) // 60
            },
            'achievements': [a.to_dict() for a in achievements]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@progress.route('/quiz-attempt', methods=['POST'])
@login_required
def record_quiz_attempt():
    """Record a quiz attempt and check for achievements"""
    try:
        data = request.get_json()
        
        # Create quiz attempt
        quiz = QuizAttempt(
            user_id=current_user.id,
            topic=data['topic'],
            score=data['score'],
            max_score=data['max_score']
        )
        db.session.add(quiz)
        
        # Add XP based on score
        xp_earned = int((quiz.score / quiz.max_score) * 100)
        leveled_up = current_user.add_xp(xp_earned)
        
        # Check for achievements
        new_achievements = check_quiz_achievements(quiz)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Quiz attempt recorded successfully',
            'xp_earned': xp_earned,
            'leveled_up': leveled_up,
            'new_achievements': [a.to_dict() for a in new_achievements]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress.route('/learning-session', methods=['POST'])
@login_required
def record_learning_session():
    """Record a learning session"""
    try:
        data = request.get_json()
        
        session = LearningSession(
            user_id=current_user.id,
            topic=data['topic'],
            duration=data['duration'],
            started_at=datetime.fromisoformat(data['started_at']),
            ended_at=datetime.fromisoformat(data['ended_at'])
        )
        db.session.add(session)
        
        # Add XP for learning time (1 XP per minute, max 30 XP per session)
        minutes = min(session.duration // 60, 30)
        leveled_up = current_user.add_xp(minutes)
        
        # Check for learning time achievements
        new_achievements = check_learning_achievements(session)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Learning session recorded successfully',
            'xp_earned': minutes,
            'leveled_up': leveled_up,
            'new_achievements': [a.to_dict() for a in new_achievements]
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def check_quiz_achievements(quiz):
    """Check and award quiz-related achievements"""
    new_achievements = []
    
    # Get all quiz attempts for the user
    user_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    total_quizzes = len(user_quizzes)
    perfect_scores = sum(1 for q in user_quizzes if q.score == q.max_score)
    
    # Quiz quantity achievements
    quiz_milestones = {
        'Quiz Beginner': 5,
        'Quiz Enthusiast': 20,
        'Quiz Master': 50
    }
    
    for name, required in quiz_milestones.items():
        if total_quizzes >= required:
            achievement = Achievement.query.filter_by(name=name).first()
            if achievement and not UserAchievement.query.filter_by(
                user_id=current_user.id, achievement_id=achievement.id).first():
                new_achievement = UserAchievement(
                    user_id=current_user.id,
                    achievement_id=achievement.id
                )
                db.session.add(new_achievement)
                new_achievements.append(new_achievement)
    
    # Perfect score achievements
    if perfect_scores >= 1:
        achievement = Achievement.query.filter_by(name='First Perfect Score').first()
        if achievement and not UserAchievement.query.filter_by(
            user_id=current_user.id, achievement_id=achievement.id).first():
            new_achievement = UserAchievement(
                user_id=current_user.id,
                achievement_id=achievement.id
            )
            db.session.add(new_achievement)
            new_achievements.append(new_achievement)
    
    return new_achievements

def check_learning_achievements(session):
    """Check and award learning time achievements"""
    new_achievements = []
    
    # Calculate total learning time
    total_time = sum(
        s.duration for s in LearningSession.query.filter_by(user_id=current_user.id).all()
        if s.duration
    )
    
    # Learning time achievements (in hours)
    time_milestones = {
        'Learning Explorer': 1,
        'Learning Enthusiast': 5,
        'Learning Master': 10
    }
    
    total_hours = total_time / 3600
    for name, required_hours in time_milestones.items():
        if total_hours >= required_hours:
            achievement = Achievement.query.filter_by(name=name).first()
            if achievement and not UserAchievement.query.filter_by(
                user_id=current_user.id, achievement_id=achievement.id).first():
                new_achievement = UserAchievement(
                    user_id=current_user.id,
                    achievement_id=achievement.id
                )
                db.session.add(new_achievement)
                new_achievements.append(new_achievement)
    
    return new_achievements

def initialize_achievements():
    """Initialize default achievements in the database"""
    default_achievements = [
        {
            'name': 'Quiz Beginner',
            'description': 'Complete 5 quizzes',
            'category': 'quiz',
            'points': 50,
            'icon': '🎯'
        },
        {
            'name': 'Quiz Enthusiast',
            'description': 'Complete 20 quizzes',
            'category': 'quiz',
            'points': 100,
            'icon': '🎯🎯'
        },
        {
            'name': 'Quiz Master',
            'description': 'Complete 50 quizzes',
            'category': 'quiz',
            'points': 200,
            'icon': '🎯🎯🎯'
        },
        {
            'name': 'First Perfect Score',
            'description': 'Get your first perfect score in a quiz',
            'category': 'quiz',
            'points': 100,
            'icon': '⭐'
        },
        {
            'name': 'Learning Explorer',
            'description': 'Spend 1 hour learning',
            'category': 'time',
            'points': 50,
            'icon': '📚'
        },
        {
            'name': 'Learning Enthusiast',
            'description': 'Spend 5 hours learning',
            'category': 'time',
            'points': 100,
            'icon': '📚📚'
        },
        {
            'name': 'Learning Master',
            'description': 'Spend 10 hours learning',
            'category': 'time',
            'points': 200,
            'icon': '📚📚📚'
        }
    ]
    
    for achievement_data in default_achievements:
        if not Achievement.query.filter_by(name=achievement_data['name']).first():
            achievement = Achievement(**achievement_data)
            db.session.add(achievement)
    
    db.session.commit()
