from flask import Blueprint, jsonify, request, render_template
from flask_login import login_required, current_user
from models import db, User, QuizAttempt, Achievement, UserAchievement, LearningSession
from datetime import datetime, timedelta, date
import os
import random

progress = Blueprint('progress', __name__)

@progress.route('/dashboard')
@login_required
def dashboard():
    # Calculate level progress
    current_level = current_user.level
    xp_for_next_level = current_level * 100  # Simple progression formula
    current_xp_in_level = current_user.total_xp - ((current_level - 1) * 100)
    level_progress = int((current_xp_in_level / xp_for_next_level) * 100)
    xp_needed = xp_for_next_level - current_xp_in_level
    
    # Get user's achievements
    user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
    earned_achievement_ids = [ua.achievement_id for ua in user_achievements]
    
    # Get all achievements with earned status
    achievements = []
    all_achievements = Achievement.query.all()
    for achievement in all_achievements:
        achievements.append({
            'name': achievement.name,
            'description': achievement.description,
            'points': achievement.points,
            'icon': get_achievement_icon(achievement.category),
            'earned': achievement.id in earned_achievement_ids
        })
    
    # Get activity data for chart
    today = date.today()
    start_date = today - timedelta(days=14)  # Last 14 days
    
    # Query learning sessions for activity chart
    sessions = LearningSession.query.filter(
        LearningSession.user_id == current_user.id,
        LearningSession.created_at >= start_date
    ).all()
    
    # Build activity data by day
    activity_data = [0] * 14
    activity_labels = []
    for i in range(14):
        day = start_date + timedelta(days=i)
        activity_labels.append(day.strftime('%b %d'))
        # Sum XP for this day
        day_xp = sum([s.xp_earned for s in sessions if s.created_at.date() == day])
        activity_data[i] = day_xp
    
    # Generate calendar days (last 28 days)
    calendar_days = []
    for i in range(27, -1, -1):
        day = today - timedelta(days=i)
        day_active = any(s.created_at.date() == day for s in sessions)
        calendar_days.append({
            'day': day.day,
            'date': day.strftime('%b %d, %Y'),
            'active': day_active
        })
    
    return render_template('dashboard.html', 
                           level_progress=level_progress,
                           xp_needed=xp_needed,
                           achievements=achievements,
                           activity_data=activity_data,
                           activity_labels=activity_labels,
                           calendar_days=calendar_days)

@progress.route('/stats', methods=['GET'])
@login_required
def get_stats():
    # Get basic stats
    stats = {
        'total_xp': current_user.total_xp,
        'level': current_user.level,
        'login_streak': current_user.login_streak
    }
    
    # Get quiz stats
    quiz_attempts = QuizAttempt.query.filter_by(user_id=current_user.id).all()
    stats['total_quizzes'] = len(quiz_attempts)
    if quiz_attempts:
        stats['avg_score'] = sum([q.score / q.max_score * 100 for q in quiz_attempts]) / len(quiz_attempts)
    else:
        stats['avg_score'] = 0
    
    return jsonify(stats)

@progress.route('/quiz-attempt', methods=['POST'])
@login_required
def record_quiz_attempt():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['topic', 'score', 'max_score']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create quiz attempt
        quiz = QuizAttempt(
            user_id=current_user.id,
            topic=data['topic'],
            score=data['score'],
            max_score=data['max_score']
        )
        
        # Add XP based on score percentage
        score_percentage = quiz.score / quiz.max_score
        xp_earned = int(10 * score_percentage)  # Max 10 XP for perfect score
        current_user.add_xp(xp_earned)
        
        db.session.add(quiz)
        db.session.commit()
        
        # Check for quiz-related achievements
        check_quiz_achievements(quiz)
        
        return jsonify({
            'message': 'Quiz attempt recorded successfully',
            'xp_earned': xp_earned,
            'new_total_xp': current_user.total_xp,
            'level': current_user.level
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@progress.route('/learning-session', methods=['POST'])
@login_required
def record_learning_session():
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['topic', 'duration_minutes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create learning session
        session = LearningSession(
            user_id=current_user.id,
            topic=data['topic'],
            duration_minutes=data['duration_minutes']
        )
        
        # Add XP based on duration (1 XP per minute, max 20)
        xp_earned = min(data['duration_minutes'], 20)
        current_user.add_xp(xp_earned)
        session.xp_earned = xp_earned
        
        db.session.add(session)
        db.session.commit()
        
        # Check for learning-related achievements
        check_learning_achievements(session)
        
        return jsonify({
            'message': 'Learning session recorded successfully',
            'xp_earned': xp_earned,
            'new_total_xp': current_user.total_xp,
            'level': current_user.level
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def get_achievement_icon(category):
    """Return Font Awesome icon class based on achievement category"""
    icons = {
        'quiz': 'fa-question-circle',
        'streak': 'fa-fire',
        'learning': 'fa-book',
        'level': 'fa-layer-group',
        'xp': 'fa-star'
    }
    return icons.get(category, 'fa-award')

def check_quiz_achievements(quiz):
    """Check and award quiz-related achievements"""
    try:
        user_id = quiz.user_id
        
        # Get count of user's quiz attempts
        quiz_count = QuizAttempt.query.filter_by(user_id=user_id).count()
        
        # Check for first quiz achievement
        if quiz_count == 1:
            award_achievement(user_id, 'First Quiz')
            
        # Check for 10 quizzes achievement
        if quiz_count == 10:
            award_achievement(user_id, 'Quiz Master')
            
        # Check for perfect score achievement
        if quiz.score == quiz.max_score:
            award_achievement(user_id, 'Perfect Score')
            
        # Check topic specific achievements
        if 'math' in quiz.topic.lower():
            award_achievement(user_id, 'Math Explorer')
        elif 'science' in quiz.topic.lower():
            award_achievement(user_id, 'Science Whiz')
            
    except Exception as e:
        print(f"Error checking quiz achievements: {str(e)}")

def check_learning_achievements(session):
    """Check and award learning time achievements"""
    try:
        user_id = session.user_id
        
        # Get total learning time
        total_minutes = db.session.query(db.func.sum(LearningSession.duration_minutes))\
            .filter_by(user_id=user_id).scalar() or 0
            
        # Check for time-based achievements
        if total_minutes >= 60:  # 1 hour
            award_achievement(user_id, 'Learning Hour')
        
        if total_minutes >= 300:  # 5 hours
            award_achievement(user_id, 'Learning Expert')
        
        # Check for diverse learning
        topic_count = db.session.query(db.func.count(db.func.distinct(LearningSession.topic)))\
            .filter_by(user_id=user_id).scalar() or 0
            
        if topic_count >= 3:
            award_achievement(user_id, 'Curious Mind')
            
    except Exception as e:
        print(f"Error checking learning achievements: {str(e)}")

def award_achievement(user_id, achievement_name):
    """Award an achievement to a user if they don't already have it"""
    # Find the achievement
    achievement = Achievement.query.filter_by(name=achievement_name).first()
    if not achievement:
        return
        
    # Check if user already has this achievement
    existing = UserAchievement.query.filter_by(
        user_id=user_id, 
        achievement_id=achievement.id
    ).first()
    
    if existing:
        return  # User already has this achievement
        
    # Award the achievement
    user_achievement = UserAchievement(
        user_id=user_id,
        achievement_id=achievement.id,
        earned_at=datetime.utcnow()
    )
    
    # Add XP for earning achievement
    user = User.query.get(user_id)
    if user:
        user.add_xp(achievement.points)
        
    db.session.add(user_achievement)
    db.session.commit()

def initialize_achievements():
    """Initialize default achievements in the database."""
    try:
        if Achievement.query.count() == 0:
            # Define default achievements
            default_achievements = [
                {
                    'name': 'First Chat',
                    'description': 'Started your first conversation with Buddy!',
                    'icon': 'fa-comments',
                    'points': 10,
                    'category': 'Chat'
                },
                {
                    'name': 'Quiz Master',
                    'description': 'Scored 100% on a quiz!',
                    'icon': 'fa-graduation-cap',
                    'points': 25,
                    'category': 'Quiz'
                },
                # Add other achievements...
            ]
            
            for achievement_data in default_achievements:
                achievement = Achievement(**achievement_data)
                db.session.add(achievement)
            
            db.session.commit()
            print("Default achievements initialized.")
    except Exception as e:
        db.session.rollback()
        print(f"Error initializing achievements: {str(e)}")

