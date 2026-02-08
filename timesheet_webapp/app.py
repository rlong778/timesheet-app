#!/usr/bin/env python3
"""
Lab Timesheet Web Application
Modern web interface for tracking lab hours and generating timesheets
"""

from flask import Flask, render_template, request, jsonify, send_file, session
from datetime import datetime, timedelta
import json
import os
import anthropic
from pdf_generator import TimesheetPDFGenerator

app = Flask(__name__)
app.secret_key = os.urandom(24)

# File to store activities
ACTIVITIES_FILE = 'lab_activities.json'
CONFIG_FILE = 'config.json'

class TimesheetManager:
    def __init__(self):
        self.load_config()
        self.anthropic_client = anthropic.Anthropic(api_key=self.config['anthropic_api_key'])
        self.pdf_generator = TimesheetPDFGenerator('Updated_Weekly_Timesheet__2_.pdf')
    
    def load_config(self):
        """Load configuration"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'user_info': {
                    'name': '',
                    'gt_id': ''
                }
            }
    
    def save_config(self, user_info):
        """Save user configuration"""
        self.config['user_info'] = user_info
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def load_activities(self):
        """Load activities from JSON file"""
        if os.path.exists(ACTIVITIES_FILE):
            with open(ACTIVITIES_FILE, 'r') as f:
                return json.load(f)
        return {}
    
    def save_activities(self, activities):
        """Save activities to JSON file"""
        with open(ACTIVITIES_FILE, 'w') as f:
            json.dump(activities, f, indent=2)
    
    def get_current_week_key(self):
        """Get the key for the current week (Monday-Sunday)"""
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        return monday.strftime('%Y-%m-%d')
    
    def get_week_dates(self, week_key):
        """Get all dates for a given week"""
        monday = datetime.strptime(week_key, '%Y-%m-%d')
        return [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    def add_activity(self, date_str, activity_text, hours=None):
        """Add an activity for a specific date"""
        activities = self.load_activities()
        
        # Parse date and get week key
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        monday = target_date - timedelta(days=target_date.weekday())
        week_key = monday.strftime('%Y-%m-%d')
        
        # Initialize week and day if needed
        if week_key not in activities:
            activities[week_key] = {}
        if date_str not in activities[week_key]:
            activities[week_key][date_str] = []
        
        # Add activity
        activity_entry = {
            'activity': activity_text,
            'timestamp': datetime.now().isoformat()
        }
        
        if hours:
            activity_entry['hours'] = hours
        
        activities[week_key][date_str].append(activity_entry)
        self.save_activities(activities)
        
        return True
    
    def get_week_data(self, week_key=None):
        """Get activities for a specific week"""
        if week_key is None:
            week_key = self.get_current_week_key()
        
        activities = self.load_activities()
        week_data = activities.get(week_key, {})
        
        # Format for display
        result = {
            'week_key': week_key,
            'days': []
        }
        
        for date in self.get_week_dates(week_key):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_data = {
                'date': date,
                'day_name': date_obj.strftime('%A'),
                'display_date': date_obj.strftime('%B %d, %Y'),
                'activities': week_data.get(date, []),
                'total_hours': sum(act.get('hours', 0) for act in week_data.get(date, []))
            }
            result['days'].append(day_data)
        
        return result
    
    def get_all_weeks(self):
        """Get all weeks in the system"""
        activities = self.load_activities()
        weeks = []
        
        for week_key in sorted(activities.keys(), reverse=True):
            week_date = datetime.strptime(week_key, '%Y-%m-%d')
            total_hours = 0
            total_entries = 0
            
            for day_data in activities[week_key].values():
                total_entries += len(day_data)
                total_hours += sum(act.get('hours', 0) for act in day_data)
            
            weeks.append({
                'week_key': week_key,
                'display_date': week_date.strftime('%B %d, %Y'),
                'total_hours': total_hours,
                'total_entries': total_entries
            })
        
        return weeks
    
    def delete_week(self, week_key):
        """Delete a week's data"""
        activities = self.load_activities()
        if week_key in activities:
            del activities[week_key]
            self.save_activities(activities)
            return True
        return False
    
    def delete_activity(self, week_key, date_str, activity_index):
        """Delete a specific activity"""
        activities = self.load_activities()
        if week_key in activities and date_str in activities[week_key]:
            if 0 <= activity_index < len(activities[week_key][date_str]):
                del activities[week_key][date_str][activity_index]
                self.save_activities(activities)
                return True
        return False
    
    async def generate_ai_summary(self, week_data):
        """Generate AI summary of weekly activities"""
        all_activities = []
        for date, activities in sorted(week_data.items()):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            for act in activities:
                all_activities.append(f"{day_name}: {act['activity']}")
        
        activities_text = "\n".join(all_activities)
        
        message = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": f"""Based on these lab activities from this week, write a brief professional summary (5-7 sentences) of what was accomplished. Focus on key achievements and research progress.

Activities:
{activities_text}

Write a cohesive paragraph suitable for a weekly timesheet report."""
            }]
        )
        
        return message.content[0].text
    
    def generate_timesheet(self, week_key):
        """Generate PDF timesheet for a week"""
        activities = self.load_activities()
        
        if week_key not in activities or not activities[week_key]:
            return None, "No activities logged for this week"
        
        week_data = activities[week_key]
        
        # Generate AI summary (synchronous version)
        import asyncio
        try:
            summary = asyncio.run(self.generate_ai_summary(week_data))
        except:
            # Fallback to basic summary
            summary = "Weekly lab activities completed as scheduled."
        
        # Prepare timesheet data
        timesheet_data = {
            'student_name': self.config['user_info']['name'],
            'gt_id': self.config['user_info']['gt_id'],
            'week_start': week_key,
            'daily_entries': [],
            'weekly_summary': summary
        }
        
        # Process daily entries
        for date in self.get_week_dates(week_key):
            if date in week_data and week_data[date]:
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                day_name = date_obj.strftime('%A')
                
                total_hours = sum(act.get('hours', 0) for act in week_data[date])
                
                if total_hours > 0:
                    time_in = "2:30 PM"
                    time_out = "5:30 PM"
                else:
                    time_in = ""
                    time_out = ""
                
                timesheet_data['daily_entries'].append({
                    'day': f"{day_name}, {date_obj.strftime('%B %d')}",
                    'date': date_obj.strftime('%m/%d/%Y'),
                    'time_in': time_in,
                    'time_out': time_out,
                    'mentor_initials': ''
                })
        
        # Generate PDF
        output_path = f"timesheet_{week_key}.pdf"
        try:
            self.pdf_generator.create_timesheet(timesheet_data, output_path)
            return output_path, summary
        except Exception as e:
            return None, str(e)

# Initialize manager
manager = TimesheetManager()

# Routes
@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET', 'POST'])
def config():
    """Get or update user configuration"""
    if request.method == 'GET':
        return jsonify(manager.config.get('user_info', {}))
    else:
        user_info = request.json
        manager.save_config(user_info)
        return jsonify({'success': True})

@app.route('/api/current-week')
def current_week():
    """Get current week's data"""
    week_data = manager.get_week_data()
    return jsonify(week_data)

@app.route('/api/week/<week_key>')
def get_week(week_key):
    """Get specific week's data"""
    week_data = manager.get_week_data(week_key)
    return jsonify(week_data)

@app.route('/api/weeks')
def all_weeks():
    """Get all weeks"""
    weeks = manager.get_all_weeks()
    return jsonify(weeks)

@app.route('/api/activity', methods=['POST'])
def add_activity():
    """Add a new activity"""
    data = request.json
    success = manager.add_activity(
        data['date'],
        data['activity'],
        data.get('hours')
    )
    return jsonify({'success': success})

@app.route('/api/activity/delete', methods=['POST'])
def delete_activity():
    """Delete an activity"""
    data = request.json
    success = manager.delete_activity(
        data['week_key'],
        data['date'],
        data['index']
    )
    return jsonify({'success': success})

@app.route('/api/week/delete', methods=['POST'])
def delete_week():
    """Delete a week"""
    data = request.json
    success = manager.delete_week(data['week_key'])
    return jsonify({'success': success})

@app.route('/api/generate-timesheet/<week_key>')
def generate_timesheet(week_key):
    """Generate timesheet PDF"""
    output_path, summary_or_error = manager.generate_timesheet(week_key)
    
    if output_path:
        return send_file(
            output_path,
            as_attachment=True,
            download_name=f"Timesheet_{manager.config['user_info']['name']}_{week_key}.pdf"
        )
    else:
        return jsonify({'error': summary_or_error}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
