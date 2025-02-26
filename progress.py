from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from models import db, QuizAttempt, Achievement, UserAchievement, LearningSession
from datetime import datetime, timedelta, date
import calendar

progress = Blueprint('progress', __name__)

@progress.route('/dashboard')
@login_required
def dashboard():
    """Render the user's dashboard"""
    try:
        # Calculate XP needed for next level (1000 XP per level)
        xp_for_next_level = (current_user.level + 1) * 1000
        xp_in_current_level = current_user.total_xp - (current_user.level * 1000)
        level_progress = (xp_in_current_level / 1000) * 100
        xp_needed = xp_for_next_level - current_user.total_xp

        # Get achievements
        all_achievements = Achievement.query.all()
        user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
        earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
        
        achievements_data = []
        for achievement in all_achievements:
            achievements_data.append({
                'name': achievement.name,
                'description': achievement.description,
                'points': achievement.points,
                'icon': achievement.icon,
                'earned': achievement.id in earned_achievement_ids
            })

        # Get activity data (last 7 days)
        today = date.today()
        activity_labels = []
        activity_data = []
        
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            activity_labels.append(day.strftime('%a'))
            
            # Get XP earned on this day
            daily_quizzes = QuizAttempt.query.filter(
                QuizAttempt.user_id == current_user.id,
                db.func.date(QuizAttempt.created_at) == day
            ).all()
            
            daily_xp = sum(quiz.score for quiz in daily_quizzes)
            activity_data.append(daily_xp)

        # Generate calendar days (last 28 days)
        calendar_days = []
        active_days = set()
        
        # Get active days from quiz attempts
        active_day_records = db.session.query(
            db.func.date(QuizAttempt.created_at)
        ).filter(
            QuizAttempt.user_id == current_user.id,
            QuizAttempt.created_at >= today - timedelta(days=28)
        ).distinct().all()
        
        active_days = set(day[0] for day in active_day_records)
        
        for i in range(27, -1, -1):
            day = today - timedelta(days=i)
            calendar_days.append({
                'day': day.day,
                'date': day.strftime('%Y-%m-%d'),
                'active': day in active_days
            })

        return render_template('dashboard.html',
            level_progress=round(level_progress, 1),
            xp_needed=xp_needed,
            achievements=achievements_data,
            activity_labels=activity_labels,
            activity_data=activity_data,
            calendar_days=calendar_days
        )
        
    except Exception as e:
        print(f"Error rendering dashboard: {str(e)}")
        return render_template('dashboard.html',
            level_progress=0,
            xp_needed=1000,
            achievements=[],
            activity_labels=[],
            activity_data=[],
            calendar_days=[]
        )

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
    """Record a quiz attempt and update user progress"""
    try:
        data = request.json
        quiz = QuizAttempt(
            user_id=current_user.id,
            topic=data['topic'],
            score=data['score'],
            max_score=data['max_score']
        )
        db.session.add(quiz)
        
        # Add XP based on score
        xp_earned = int((quiz.score / quiz.max_score) * 100)
        current_user.add_xp(xp_earned)
        
        # Check for achievements
        check_quiz_achievements(quiz)
        
        db.session.commit()
        return jsonify({'message': 'Quiz attempt recorded', 'xp_earned': xp_earned})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress.route('/learning-session', methods=['POST'])
@login_required
def record_learning_session():
    """Record a learning session"""
    try:
        data = request.json
        session = LearningSession(
            user_id=current_user.id,
            topic=data['topic'],
            duration=data['duration'],
            started_at=datetime.fromisoformat(data['started_at']),
            ended_at=datetime.fromisoformat(data['ended_at'])
        )
        db.session.add(session)
        
        # Add XP based on duration (1 XP per minute, max 60 XP per session)
        minutes = min(session.duration // 60, 60)
        current_user.add_xp(minutes)
        
        # Check for achievements
        check_learning_achievements(session)
        
        db.session.commit()
        return jsonify({'message': 'Learning session recorded', 'xp_earned': minutes})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def check_quiz_achievements(quiz):
    """Check and award quiz-related achievements"""
    try:
        # Get all quiz attempts for the user
        user_quizzes = QuizAttempt.query.filter_by(user_id=current_user.id).all()
        total_quizzes = len(user_quizzes)
        perfect_scores = sum(1 for q in user_quizzes if q.score == q.max_score)
        
        # Define achievement conditions
        achievement_conditions = {
            'quiz_novice': total_quizzes >= 5,
            'quiz_master': total_quizzes >= 50,
            'perfect_score': quiz.score == quiz.max_score,
            'perfect_streak': perfect_scores >= 5
        }
        
        # Check each achievement
        for achievement_name, condition in achievement_conditions.items():
            if condition:
                achievement = Achievement.query.filter_by(name=achievement_name).first()
                if achievement:
                    existing = UserAchievement.query.filter_by(
                        user_id=current_user.id,
                        achievement_id=achievement.id
                    ).first()
                    
                    if not existing:
                        user_achievement = UserAchievement(
                            user_id=current_user.id,
                            achievement_id=achievement.id
                        )
                        db.session.add(user_achievement)
                        current_user.add_xp(achievement.points)
                        
    except Exception as e:
        print(f"Error checking quiz achievements: {str(e)}")

def check_learning_achievements(session):
    """Check and award learning time achievements"""
    try:
        # Get total learning time
        total_time = db.session.query(db.func.sum(LearningSession.duration))\
            .filter_by(user_id=current_user.id)\
            .scalar() or 0
        
        # Define achievement conditions (time in seconds)
        achievement_conditions = {
            'time_1hour': total_time >= 3600,
            'time_5hours': total_time >= 18000,
            'time_10hours': total_time >= 36000
        }
        
        # Check each achievement
        for achievement_name, condition in achievement_conditions.items():
            if condition:
                achievement = Achievement.query.filter_by(name=achievement_name).first()
                if achievement:
                    existing = UserAchievement.query.filter_by(
                        user_id=current_user.id,
                        achievement_id=achievement.id
                    ).first()
                    
                    if not existing:
                        user_achievement = UserAchievement(
                            user_id=current_user.id,
                            achievement_id=achievement.id
                        )
                        db.session.add(user_achievement)
                        current_user.add_xp(achievement.points)
                        
    except Exception as e:
        print(f"Error checking learning achievements: {str(e)}")

def initialize_achievements():
    """Initialize default achievements in the database"""
    default_achievements = [
        {
            'name': 'quiz_novice',
            'description': 'Complete 5 quizzes',
            'category': 'quiz',
            'points': 50,
            'icon': 'fa-star'
        },
        {
            'name': 'quiz_master',
            'description': 'Complete 50 quizzes',
            'category': 'quiz',
            'points': 200,
            'icon': 'fa-crown'
        },
        {
            'name': 'perfect_score',
            'description': 'Get a perfect score on a quiz',
            'category': 'quiz',
            'points': 100,
            'icon': 'fa-check-circle'
        },
        {
            'name': 'perfect_streak',
            'description': 'Get 5 perfect scores in a row',
            'category': 'quiz',
            'points': 300,
            'icon': 'fa-fire'
        },
        {
            'name': 'time_1hour',
            'description': 'Spend 1 hour learning',
            'category': 'time',
            'points': 100,
            'icon': 'fa-clock'
        },
        {
            'name': 'time_5hours',
            'description': 'Spend 5 hours learning',
            'category': 'time',
            'points': 300,
            'icon': 'fa-hourglass'
        },
        {
            'name': 'time_10hours',
            'description': 'Spend 10 hours learning',
            'category': 'time',
            'points': 500,
            'icon': 'fa-graduation-cap'
        }
    ]
    
    try:
        for achievement_data in default_achievements:
            existing = Achievement.query.filter_by(name=achievement_data['name']).first()
            if not existing:
                achievement = Achievement(**achievement_data)
                db.session.add(achievement)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing achievements: {str(e)}")
