\#!/usr/bin/env python3
"""
Timesheet Automation Bot
Receives daily lab activities via Telegram and generates weekly timesheets
"""

import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.ext import JobQueue
import anthropic
from pdf_generator import TimesheetPDFGenerator

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# File to store daily activities - use absolute path so data persists regardless of working directory
ACTIVITIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lab_activities.json')

class TimesheetBot:
    def __init__(self, telegram_token, anthropic_api_key, user_info, reminder_time="17:00"):
        self.telegram_token = telegram_token
        self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.user_info = user_info
        # Initialize PDF generator with template path (absolute path for reliability)
        template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Updated_Weekly_Timesheet__2_.pdf')
        self.pdf_generator = TimesheetPDFGenerator(template_path)
        self.reminder_time = reminder_time  # Default 5:00 PM
        self.user_chat_id = None  # Will be set on first message
        
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
        # Get Monday of current week
        monday = today - timedelta(days=today.weekday())
        return monday.strftime('%Y-%m-%d')
    
    def get_week_dates(self, week_key):
        """Get all dates for a given week"""
        monday = datetime.strptime(week_key, '%Y-%m-%d')
        return [(monday + timedelta(days=i)).strftime('%Y-%m-%d') 
                for i in range(7)]
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        # Save user's chat ID for reminders
        self.user_chat_id = update.effective_chat.id
        
        keyboard = [
            ['ðŸ“ Log Today', 'ðŸ“Š View Week'],
            ['â®ï¸ Backlog Entry', 'ðŸ“… Past Weeks'],
            ['â° Backlog Week', 'ðŸ“† Month Calendar'],
            ['ðŸ“Š Monthly Hours', 'ðŸ”” Set Reminder'],
            ['âœ… Generate Timesheet', 'ðŸ“§ Email to Mentor'],
            ['ðŸ—‘ï¸ Clear Week']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        welcome_message = """
ðŸ”¬ Welcome to the Lab Timesheet Bot!

Here's how it works:

ðŸ“ *Log Today* - Record what you did in lab today
ðŸ“Š *View Week* - See all your activities this week
â®ï¸ *Backlog Entry* - Log activities for a single past date
ðŸ“… *Past Weeks* - View/generate timesheets for previous weeks
â° *Backlog Week* - Quickly backlog M-F with 2:30-5:30 PM times
ðŸ“† *Month Calendar* - See all Mondays this month with dates
ðŸ“Š *Monthly Hours* - See total hours worked this month
ðŸ”” *Set Reminder* - Daily reminder to log your hours
âœ… *Generate Timesheet* - Create your filled PDF timesheet
ðŸ“§ *Email to Mentor* - Generate & email timesheet to mentor
ðŸ—‘ï¸ *Clear Week* - Start fresh (clear this week's data)

Or just send me a message like:
"Ran PCR samples and analyzed gel results. 3.5 hours"

I'll automatically track it for today!
        """
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup
        )
    
    async def log_activity(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                          activity_text: str, hours: float = None, date_str: str = None):
        """Log an activity for today or a specific date"""
        activities = self.load_activities()
        
        # Use provided date or today
        if date_str:
            target_date = datetime.strptime(date_str, '%Y-%m-%d')
        else:
            target_date = datetime.now()
        
        # Get week key for the target date
        monday = target_date - timedelta(days=target_date.weekday())
        week_key = monday.strftime('%Y-%m-%d')
        today = target_date.strftime('%Y-%m-%d')
        
        # Initialize week if needed
        if week_key not in activities:
            activities[week_key] = {}
        
        # Initialize today if needed
        if today not in activities[week_key]:
            activities[week_key][today] = []
        
        # Add activity
        activity_entry = {
            'activity': activity_text,
            'timestamp': datetime.now().isoformat()
        }
        
        if hours:
            activity_entry['hours'] = hours
            
        activities[week_key][today].append(activity_entry)
        self.save_activities(activities)
        
        response = f"âœ… Logged for {target_date.strftime('%A, %B %d, %Y')}:\n\n{activity_text}"
        if hours:
            response += f"\n\nâ±ï¸ Hours: {hours}"
        
        await update.message.reply_text(response)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages"""
        text = update.message.text
        
        # Check for button commands
        if text == 'ðŸ“ Log Today':
            await update.message.reply_text(
                "ðŸ“ What did you work on today?\n\n"
                "Example: 'Cultured cells and prepared slides. 4 hours'"
            )
            return
        elif text == 'ðŸ“Š View Week':
            await self.view_week(update, context)
            return
        elif text == 'â®ï¸ Backlog Entry':
            await self.backlog_prompt(update, context)
            return
        elif text == 'ðŸ“… Past Weeks':
            await self.show_past_weeks(update, context)
            return
        elif text == 'â° Backlog Week':
            await self.backlog_week_prompt(update, context)
            return
        elif text == 'ðŸ“† Month Calendar':
            await self.show_month_calendar(update, context)
            return
        elif text == 'ðŸ“Š Monthly Hours':
            await self.show_monthly_hours(update, context)
            return
        elif text == 'ðŸ”” Set Reminder':
            await self.set_reminder_prompt(update, context)
            return
        elif text == 'âœ… Generate Timesheet':
            # Check if in past week mode
            if context.user_data.get('past_week_action_mode'):
                await self.generate_past_week_timesheet(update, context)
                return
            await self.generate_timesheet(update, context)
            return
        elif text == 'ðŸ“§ Email to Mentor':
            await self.email_to_mentor(update, context)
            return
        elif text == 'ðŸ—‘ï¸ Clear Week':
            await self.clear_week(update, context)
            return
        elif text == 'ðŸ—‘ï¸ Delete This Week':
            if context.user_data.get('past_week_action_mode'):
                await self.delete_past_week(update, context)
                return
        elif text == 'âŒ Cancel':
            if context.user_data.get('past_week_action_mode'):
                context.user_data['past_week_action_mode'] = False
                context.user_data.pop('selected_past_week', None)
                await update.message.reply_text("âŒ Cancelled.")
                return
            elif context.user_data.get('backlog_week_mode'):
                context.user_data['backlog_week_mode'] = False
                await update.message.reply_text("âŒ Cancelled.")
                return
        
        # Check if user is in backlog week mode
        if context.user_data.get('backlog_week_mode'):
            await self.process_backlog_week(update, context)
            return
        
        # Check if user is setting reminder
        if context.user_data.get('setting_reminder'):
            await self.process_reminder_setting(update, context)
            return
        
        # Check if user is in backlog mode
        if context.user_data.get('backlog_mode'):
            await self.process_backlog_entry(update, context)
            return
        
        # Check if user is entering backlog activity
        if context.user_data.get('entering_backlog_activity'):
            if text.lower() == 'cancel':
                context.user_data['entering_backlog_activity'] = False
                context.user_data.pop('backlog_date', None)
                await update.message.reply_text("âŒ Backlog cancelled.")
                return
            
            # Parse activity
            hours = None
            activity_text = text
            
            import re
            hours_match = re.search(r'(\d+\.?\d*)\s*(hours?|h)', text.lower())
            if hours_match:
                hours = float(hours_match.group(1))
                activity_text = re.sub(r'\d+\.?\d*\s*hours?|\d+\.?\d*h', '', text, flags=re.IGNORECASE).strip()
            
            # Log for the backlog date
            backlog_date = context.user_data.get('backlog_date')
            await self.log_activity(update, context, activity_text, hours, backlog_date)
            
            # Clear backlog mode
            context.user_data['entering_backlog_activity'] = False
            context.user_data.pop('backlog_date', None)
            return
        
        # Check if user is selecting a past week
        if context.user_data.get('selecting_past_week'):
            await self.process_past_week_selection(update, context)
            return
        
        # Check if in past week action mode and viewing week
        if context.user_data.get('past_week_action_mode') and text == 'ðŸ“Š View This Week':
            selected_week = context.user_data.get('selected_past_week')
            if selected_week:
                await self.view_specific_week(update, context, selected_week)
            return
        
        # Parse activity (try to extract hours if mentioned)
        hours = None
        activity_text = text
        
        # Simple parsing for hours (e.g., "3 hours", "3.5 hours", "3h")
        import re
        hours_match = re.search(r'(\d+\.?\d*)\s*(hours?|h)', text.lower())
        if hours_match:
            hours = float(hours_match.group(1))
            # Remove hours from activity text
            activity_text = re.sub(r'\d+\.?\d*\s*hours?|\d+\.?\d*h', '', text, flags=re.IGNORECASE).strip()
        
        await self.log_activity(update, context, activity_text, hours)
    
    async def view_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """View activities for current week"""
        activities = self.load_activities()
        week_key = self.get_current_week_key()
        
        if week_key not in activities or not activities[week_key]:
            await update.message.reply_text("ðŸ“­ No activities logged this week yet!")
            return
        
        week_data = activities[week_key]
        message = f"ðŸ“Š *Week of {week_key}*\n\n"
        
        for date in self.get_week_dates(week_key):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            
            if date in week_data and week_data[date]:
                total_hours = sum(act.get('hours', 0) for act in week_data[date])
                message += f"*{day_name} ({date_obj.strftime('%m/%d')})*"
                if total_hours > 0:
                    message += f" - {total_hours}h"
                message += "\n"
                
                for act in week_data[date]:
                    message += f"  â€¢ {act['activity']}\n"
                message += "\n"
        
        await update.message.reply_text(message)
    
    async def clear_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Clear current week's data"""
        activities = self.load_activities()
        week_key = self.get_current_week_key()
        
        if week_key in activities:
            del activities[week_key]
            self.save_activities(activities)
            await update.message.reply_text("ðŸ—‘ï¸ Cleared this week's activities!")
        else:
            await update.message.reply_text("ðŸ“­ No activities to clear!")
    
    async def backlog_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt user to enter a backlog date"""
        await update.message.reply_text(
            "â®ï¸ *Backlog Entry*\n\n"
            "Enter the date you want to log activities for.\n\n"
            "Format: YYYY-MM-DD or MM/DD/YYYY\n"
            "Examples:\n"
            "â€¢ 2026-01-15\n"
            "â€¢ 01/15/2026\n\n"
            "Can backlog up to 2 months (60 days).\n\n"
            "Or send 'cancel' to go back."
        )
        context.user_data['backlog_mode'] = True
    
    async def process_backlog_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process the backlog date entry"""
        text = update.message.text.strip()
        
        if text.lower() == 'cancel':
            context.user_data['backlog_mode'] = False
            await update.message.reply_text("âŒ Backlog cancelled.")
            return
        
        # Try to parse the date
        target_date = None
        try:
            # Try YYYY-MM-DD format
            target_date = datetime.strptime(text, '%Y-%m-%d')
        except ValueError:
            try:
                # Try MM/DD/YYYY format
                target_date = datetime.strptime(text, '%m/%d/%Y')
            except ValueError:
                await update.message.reply_text(
                    "âŒ Invalid date format.\n\n"
                    "Please use:\n"
                    "â€¢ YYYY-MM-DD (e.g., 2026-01-15)\n"
                    "â€¢ MM/DD/YYYY (e.g., 01/15/2026)\n\n"
                    "Or send 'cancel' to go back."
                )
                return
        
        # Check if date is within last 2 months (60 days)
        two_months_ago = datetime.now() - timedelta(days=60)
        if target_date < two_months_ago or target_date > datetime.now():
            await update.message.reply_text(
                "âŒ Date must be within the last 60 days and not in the future.\n\n"
                "Try again or send 'cancel'."
            )
            return
        
        # Store the target date and prompt for activity
        context.user_data['backlog_date'] = target_date.strftime('%Y-%m-%d')
        context.user_data['backlog_mode'] = False
        context.user_data['entering_backlog_activity'] = True
        
        await update.message.reply_text(
            f"âœ… Logging for: {target_date.strftime('%A, %B %d, %Y')}\n\n"
            f"Now enter what you did on that day:\n\n"
            f"Example: 'Cultured cells and ran experiments. 4 hours'\n\n"
            f"Or send 'cancel' to go back."
        )
    
    async def show_past_weeks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available past weeks"""
        activities = self.load_activities()
        
        if not activities:
            await update.message.reply_text("ðŸ“­ No past weeks found!")
            return
        
        # Get all weeks within last 2 months (60 days)
        two_months_ago = datetime.now() - timedelta(days=60)
        recent_weeks = []
        
        for week_key in sorted(activities.keys(), reverse=True):
            week_date = datetime.strptime(week_key, '%Y-%m-%d')
            if week_date >= two_months_ago:
                # Count activities
                total_activities = sum(len(activities[week_key][day]) for day in activities[week_key])
                # Count total hours
                total_hours = 0
                for day_data in activities[week_key].values():
                    total_hours += sum(act.get('hours', 0) for act in day_data)
                recent_weeks.append((week_key, total_activities, total_hours))
        
        if not recent_weeks:
            await update.message.reply_text("ðŸ“­ No weeks found in the last 2 months!")
            return
        
        message = "ðŸ“… *Past Weeks (Last 2 Months)*\n\n"
        message += "Reply with the week number to view or generate that week's timesheet:\n\n"
        
        for i, (week_key, count, hours) in enumerate(recent_weeks, 1):
            week_date = datetime.strptime(week_key, '%Y-%m-%d')
            message += f"{i}. Week of {week_date.strftime('%b %d, %Y')}"
            if hours > 0:
                message += f" ({hours:.1f}h, {count} entries)"
            else:
                message += f" ({count} entries)"
            message += "\n"
        
        message += "\nSend the number (1, 2, 3...) or 'cancel'"
        
        context.user_data['past_weeks_list'] = [w[0] for w in recent_weeks]
        context.user_data['selecting_past_week'] = True
        
        await update.message.reply_text(message)
    
    async def process_past_week_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process past week selection"""
        text = update.message.text.strip()
        
        if text.lower() == 'cancel':
            context.user_data['selecting_past_week'] = False
            context.user_data.pop('past_weeks_list', None)
            await update.message.reply_text("âŒ Cancelled.")
            return
        
        # Try to parse the number
        try:
            week_num = int(text)
            past_weeks = context.user_data.get('past_weeks_list', [])
            
            if week_num < 1 or week_num > len(past_weeks):
                await update.message.reply_text(
                    f"âŒ Please enter a number between 1 and {len(past_weeks)}, or 'cancel'"
                )
                return
            
            selected_week = past_weeks[week_num - 1]
            context.user_data['selected_past_week'] = selected_week
            context.user_data['selecting_past_week'] = False
            
            # Show options for this week
            week_date = datetime.strptime(selected_week, '%Y-%m-%d')
            keyboard = [
                ['ðŸ“Š View This Week', 'âœ… Generate Timesheet'],
                ['ðŸ—‘ï¸ Delete This Week', 'âŒ Cancel']
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
            
            await update.message.reply_text(
                f"Selected: Week of {week_date.strftime('%B %d, %Y')}\n\n"
                f"What would you like to do?",
                reply_markup=reply_markup
            )
            
            context.user_data['past_week_action_mode'] = True
            
        except ValueError:
            await update.message.reply_text(
                "âŒ Please enter a valid number or 'cancel'"
            )
    

    
    async def view_specific_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE, week_key: str):
        """View activities for a specific week"""
        activities = self.load_activities()
        
        if week_key not in activities or not activities[week_key]:
            await update.message.reply_text("ðŸ“­ No activities found for this week!")
            return
        
        week_data = activities[week_key]
        week_date = datetime.strptime(week_key, '%Y-%m-%d')
        message = f"ðŸ“Š *Week of {week_date.strftime('%B %d, %Y')}*\n\n"
        
        week_dates = [(week_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        
        for date in week_dates:
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            
            if date in week_data and week_data[date]:
                total_hours = sum(act.get('hours', 0) for act in week_data[date])
                message += f"*{day_name} ({date_obj.strftime('%m/%d')})*"
                if total_hours > 0:
                    message += f" - {total_hours}h"
                message += "\n"
                
                for act in week_data[date]:
                    message += f"  â€¢ {act['activity']}\n"
                message += "\n"
        
        await update.message.reply_text(message)
    
    async def delete_past_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Delete a past week's data"""
        selected_week = context.user_data.get('selected_past_week')
        if not selected_week:
            await update.message.reply_text("âŒ No week selected!")
            return
        
        activities = self.load_activities()
        
        if selected_week in activities:
            week_date = datetime.strptime(selected_week, '%Y-%m-%d')
            del activities[selected_week]
            self.save_activities(activities)
            await update.message.reply_text(
                f"ðŸ—‘ï¸ Deleted week of {week_date.strftime('%B %d, %Y')}!"
            )
        else:
            await update.message.reply_text("âŒ Week not found!")
        
        # Clear context
        context.user_data['past_week_action_mode'] = False
        context.user_data.pop('selected_past_week', None)
    
    async def generate_past_week_timesheet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate timesheet for a past week"""
        selected_week = context.user_data.get('selected_past_week')
        if not selected_week:
            await update.message.reply_text("âŒ No week selected!")
            return
        
        await update.message.reply_text("â³ Generating timesheet for past week...")
        
        activities = self.load_activities()
        
        if selected_week not in activities or not activities[selected_week]:
            await update.message.reply_text("âŒ No activities found for this week!")
            return
        
        week_data = activities[selected_week]
        
        try:
            # Generate AI summary
            await update.message.reply_text("ðŸ¤– Generating AI summary...")
            summary = await self.generate_ai_summary(week_data)
            
            # Prepare timesheet data
            week_date = datetime.strptime(selected_week, '%Y-%m-%d')
            timesheet_data = {
                'student_name': self.user_info['name'],
                'gt_id': self.user_info['gt_id'],
                'week_start': selected_week,
                'daily_entries': [],
                'weekly_summary': summary
            }
            
            # Process daily entries
            week_dates = [(week_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
            
            for date in week_dates:
                if date in week_data and week_data[date]:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    day_name = date_obj.strftime('%A')
                    
                    # Calculate total hours
                    total_hours = sum(act.get('hours', 0) for act in week_data[date])
                    
                    # Use standard lab hours: 2:30 PM - 5:30 PM
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
            output_path = f"timesheet_{selected_week}.pdf"
            self.pdf_generator.create_timesheet(timesheet_data, output_path)
            
            # Send PDF
            await update.message.reply_text("âœ… Timesheet generated!")
            await update.message.reply_document(
                document=open(output_path, 'rb'),
                filename=f"Timesheet_{self.user_info['name']}_{selected_week}.pdf",
                caption=f"ðŸ“„ Your timesheet for week of {week_date.strftime('%B %d, %Y')}\n\n"
                       f"Weekly Summary:\n{summary[:200]}..."
            )
            
            # Cleanup
            os.remove(output_path)
            
            # Clear context
            context.user_data['past_week_action_mode'] = False
            context.user_data.pop('selected_past_week', None)
            
        except Exception as e:
            logger.error(f"Error generating timesheet: {e}")
            await update.message.reply_text(f"âŒ Error generating timesheet: {str(e)}")
    
    
    async def backlog_week_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt user to backlog an entire week"""
        await update.message.reply_text(
            "â° *Bulk Backlog Week*\n\n"
            "This will log activities with:\n"
            "â€¢ Time: 2:30 PM - 5:30 PM (3 hours)\n\n"
            "Enter the Monday date of the week:\n\n"
            "Format: YYYY-MM-DD or MM/DD/YYYY\n"
            "Examples:\n"
            "â€¢ 2026-01-06 (Monday)\n"
            "â€¢ 01/06/2026 (Monday)\n\n"
            "Or just say:\n"
            "â€¢ 'week of January 6'\n"
            "â€¢ 'week of 01/06'\n\n"
            "Send 'cancel' to go back."
        )
        context.user_data['backlog_week_mode'] = True
    
    async def process_backlog_week(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process bulk week backlog"""
        text = update.message.text.strip()
        
        if text.lower() == 'cancel':
            context.user_data['backlog_week_mode'] = False
            context.user_data.pop('backlog_week_start', None)
            context.user_data.pop('backlog_days_worked', None)
            await update.message.reply_text("âŒ Bulk backlog cancelled.")
            return
        
        # If we don't have the week start date yet
        if 'backlog_week_start' not in context.user_data:
            # Try to parse the date
            monday_date = None
            
            # Check for natural language like "week of January 6"
            import re
            natural_match = re.search(r'week of (\w+)\s+(\d+)', text.lower())
            if natural_match:
                month_name = natural_match.group(1)
                day = int(natural_match.group(2))
                
                # Try to parse month
                try:
                    # Get current year or specify
                    current_year = datetime.now().year
                    date_str = f"{month_name} {day} {current_year}"
                    test_date = datetime.strptime(date_str, '%B %d %Y')
                    
                    # Find the Monday of that week
                    days_to_monday = test_date.weekday()
                    monday_date = test_date - timedelta(days=days_to_monday)
                except ValueError:
                    try:
                        date_str = f"{month_name} {day} {current_year}"
                        test_date = datetime.strptime(date_str, '%b %d %Y')
                        days_to_monday = test_date.weekday()
                        monday_date = test_date - timedelta(days=days_to_monday)
                    except ValueError:
                        pass
            
            if not monday_date:
                # Try standard date formats
                try:
                    # Try YYYY-MM-DD format
                    monday_date = datetime.strptime(text, '%Y-%m-%d')
                except ValueError:
                    try:
                        # Try MM/DD/YYYY format
                        monday_date = datetime.strptime(text, '%m/%d/%Y')
                    except ValueError:
                        try:
                            # Try MM/DD format (assume current year)
                            current_year = datetime.now().year
                            monday_date = datetime.strptime(f"{text}/{current_year}", '%m/%d/%Y')
                        except ValueError:
                            await update.message.reply_text(
                                "âŒ Invalid date format.\n\n"
                                "Please use:\n"
                                "â€¢ YYYY-MM-DD (e.g., 2026-01-06)\n"
                                "â€¢ MM/DD/YYYY (e.g., 01/06/2026)\n"
                                "â€¢ 'week of January 6'\n"
                                "â€¢ 'week of 01/06'\n\n"
                                "Send 'cancel' to go back."
                            )
                            return
                
                # If not already Monday, find the Monday of that week
                if monday_date.weekday() != 0:
                    days_to_monday = monday_date.weekday()
                    monday_date = monday_date - timedelta(days=days_to_monday)
            
            # Check if date is within last 60 days (increased from 30)
            sixty_days_ago = datetime.now() - timedelta(days=60)
            if monday_date < sixty_days_ago or monday_date > datetime.now():
                await update.message.reply_text(
                    "âŒ Date must be within the last 60 days and not in the future.\n\n"
                    "Try again or send 'cancel'."
                )
                return
            
            # Store the week start
            context.user_data['backlog_week_start'] = monday_date.strftime('%Y-%m-%d')
            
            await update.message.reply_text(
                f"âœ… Week of {monday_date.strftime('%B %d, %Y')}\n\n"
                f"Which days did you work?\n\n"
                f"Type the days separated by spaces or commas:\n\n"
                f"Examples:\n"
                f"â€¢ monday tuesday wednesday thursday friday\n"
                f"â€¢ mon tue wed thu fri\n"
                f"â€¢ m t w th f\n"
                f"â€¢ monday, wednesday, friday\n"
                f"â€¢ all weekdays (for Mon-Fri)\n\n"
                f"Send 'cancel' to go back."
            )
            return
        
        # If we have week start but not days selection
        if 'backlog_days_worked' not in context.user_data:
            if text.lower() == 'cancel':
                context.user_data['backlog_week_mode'] = False
                context.user_data.pop('backlog_week_start', None)
                await update.message.reply_text("âŒ Bulk backlog cancelled.")
                return
            
            # Parse which days they worked
            text_lower = text.lower()
            
            # Map of day variations to day names
            day_map = {
                'monday': 'Monday', 'mon': 'Monday', 'm': 'Monday',
                'tuesday': 'Tuesday', 'tue': 'Tuesday', 'tues': 'Tuesday', 't': 'Tuesday',
                'wednesday': 'Wednesday', 'wed': 'Wednesday', 'w': 'Wednesday',
                'thursday': 'Thursday', 'thu': 'Thursday', 'thur': 'Thursday', 'th': 'Thursday',
                'friday': 'Friday', 'fri': 'Friday', 'f': 'Friday',
            }
            
            # Check for "all weekdays"
            if 'all' in text_lower and ('weekday' in text_lower or 'week' in text_lower):
                selected_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday']
            else:
                # Parse individual days
                selected_days = []
                for key, day_name in day_map.items():
                    if key in text_lower.split() or key in text_lower.replace(',', ' ').split():
                        if day_name not in selected_days:
                            selected_days.append(day_name)
            
            if not selected_days:
                await update.message.reply_text(
                    "âŒ Couldn't understand which days.\n\n"
                    "Try:\n"
                    "â€¢ monday tuesday wednesday\n"
                    "â€¢ mon wed fri\n"
                    "â€¢ all weekdays\n\n"
                    "Send 'cancel' to go back."
                )
                return
            
            # Store selected days
            context.user_data['backlog_days_worked'] = selected_days
            
            # Format day list
            day_list = ", ".join(selected_days)
            
            await update.message.reply_text(
                f"âœ… Days: {day_list}\n\n"
                f"Now describe what you did during those days:\n\n"
                f"Example: 'Lab work including cell culture, PCR, and data analysis.'\n\n"
                f"Send 'cancel' to go back."
            )
            return
        
        # We have week start and days, now process the activity
        if text.lower() == 'cancel':
            context.user_data['backlog_week_mode'] = False
            context.user_data.pop('backlog_week_start', None)
            context.user_data.pop('backlog_days_worked', None)
            await update.message.reply_text("âŒ Bulk backlog cancelled.")
            return
        
        # Get the week start and selected days
        week_start_str = context.user_data.get('backlog_week_start')
        selected_days = context.user_data.get('backlog_days_worked', [])
        week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
        
        # Log for selected days only
        activities = self.load_activities()
        week_key = week_start.strftime('%Y-%m-%d')
        
        # Initialize week if needed
        if week_key not in activities:
            activities[week_key] = {}
        
        # Map day names to day numbers (0=Monday, 1=Tuesday, etc.)
        day_to_num = {
            'Monday': 0, 'Tuesday': 1, 'Wednesday': 2, 
            'Thursday': 3, 'Friday': 4, 'Saturday': 5, 'Sunday': 6
        }
        
        days_logged = []
        for day_name in selected_days:
            if day_name in day_to_num:
                day_num = day_to_num[day_name]
                date = week_start + timedelta(days=day_num)
                date_str = date.strftime('%Y-%m-%d')
                
                # Initialize day if needed
                if date_str not in activities[week_key]:
                    activities[week_key][date_str] = []
                
                # Add activity with standard hours
                activity_entry = {
                    'activity': text,
                    'timestamp': datetime.now().isoformat(),
                    'hours': 3.0  # 2:30 PM to 5:30 PM = 3 hours
                }
                
                activities[week_key][date_str].append(activity_entry)
                days_logged.append(date.strftime('%A, %b %d'))
        
        self.save_activities(activities)
        
        # Clear backlog mode
        context.user_data['backlog_week_mode'] = False
        context.user_data.pop('backlog_week_start', None)
        context.user_data.pop('backlog_days_worked', None)
        
        await update.message.reply_text(
            f"âœ… *Days Backlogged!*\n\n"
            f"Logged for:\n" + "\n".join(f"  â€¢ {day}" for day in days_logged) + "\n\n"
            f"Time: 2:30 PM - 5:30 PM (3 hours/day)\n"
            f"Activity: {text[:100]}{'...' if len(text) > 100 else ''}\n\n"
            f"Total: {len(days_logged)} days Ã— 3 hours = {len(days_logged) * 3} hours\n\n"
            f"Use 'ðŸ“… Past Weeks' to generate the timesheet!"
        )
    
    
    async def show_month_calendar(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all Mondays for the current month and last month"""
        today = datetime.now()
        
        # Get current month and last month
        current_month = today.replace(day=1)
        last_month = (current_month - timedelta(days=1)).replace(day=1)
        
        message = "ðŸ“† *Monday Dates for Backlogging*\n\n"
        
        # Function to get all Mondays in a month
        def get_mondays(year, month):
            mondays = []
            # Start from first day of month
            date = datetime(year, month, 1)
            # Find first Monday
            days_until_monday = (7 - date.weekday()) % 7
            if days_until_monday > 0:
                date = date + timedelta(days=days_until_monday)
            
            # Get all Mondays in the month
            while date.month == month:
                mondays.append(date)
                date = date + timedelta(days=7)
            
            return mondays
        
        # Last month
        last_month_mondays = get_mondays(last_month.year, last_month.month)
        message += f"*{last_month.strftime('%B %Y')}:*\n"
        for monday in last_month_mondays:
            message += f"  â€¢ {monday.strftime('%A, %B %d')} â†’ `{monday.strftime('%m/%d/%Y')}`\n"
        message += "\n"
        
        # Current month
        current_month_mondays = get_mondays(current_month.year, current_month.month)
        message += f"*{current_month.strftime('%B %Y')}:*\n"
        for monday in current_month_mondays:
            # Mark if it's this week
            week_start = today - timedelta(days=today.weekday())
            if monday.date() == week_start.date():
                message += f"  â€¢ {monday.strftime('%A, %B %d')} â†’ `{monday.strftime('%m/%d/%Y')}` â­ (This week)\n"
            else:
                message += f"  â€¢ {monday.strftime('%A, %B %d')} â†’ `{monday.strftime('%m/%d/%Y')}`\n"
        
        message += "\nðŸ’¡ *Tip:* Tap any date to copy it, then use 'â° Backlog Week'"
        
        await update.message.reply_text(message)
    
    async def show_monthly_hours(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show total hours worked this month"""
        activities = self.load_activities()
        today = datetime.now()
        
        # Get first day of current month
        month_start = today.replace(day=1)
        month_name = month_start.strftime('%B %Y')
        
        # Calculate total hours for the month
        total_hours = 0
        days_worked = 0
        week_breakdown = {}
        
        for week_key, week_data in activities.items():
            week_date = datetime.strptime(week_key, '%Y-%m-%d')
            
            # Check if any day in this week is in the current month
            for date_str, day_activities in week_data.items():
                date = datetime.strptime(date_str, '%Y-%m-%d')
                
                # If this date is in the current month
                if date.month == today.month and date.year == today.year:
                    day_hours = sum(act.get('hours', 0) for act in day_activities)
                    if day_hours > 0:
                        total_hours += day_hours
                        days_worked += 1
                        
                        # Add to week breakdown
                        if week_key not in week_breakdown:
                            week_breakdown[week_key] = 0
                        week_breakdown[week_key] += day_hours
        
        # Build message
        message = f"ðŸ“Š *Monthly Hours Summary*\n\n"
        message += f"*{month_name}*\n\n"
        
        if total_hours == 0:
            message += "ðŸ“­ No hours logged this month yet!"
        else:
            message += f"ðŸ• *Total Hours:* {total_hours:.1f} hours\n"
            message += f"ðŸ“… *Days Worked:* {days_worked} days\n"
            message += f"â±ï¸ *Average:* {total_hours/days_worked:.1f} hours/day\n\n"
            
            # Week-by-week breakdown
            if week_breakdown:
                message += "*Week-by-Week Breakdown:*\n"
                for week_key in sorted(week_breakdown.keys()):
                    week_date = datetime.strptime(week_key, '%Y-%m-%d')
                    week_hours = week_breakdown[week_key]
                    message += f"  â€¢ Week of {week_date.strftime('%b %d')}: {week_hours:.1f} hours\n"
        
        await update.message.reply_text(message)
    
    
    async def set_reminder_prompt(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Prompt to set daily reminder time"""
        current_time = getattr(self, 'reminder_time', '17:00')
        
        await update.message.reply_text(
            f"ðŸ”” *Daily Reminder Settings*\n\n"
            f"Current reminder time: {current_time}\n\n"
            f"Enter a time for your daily reminder (24-hour format):\n\n"
            f"Examples:\n"
            f"â€¢ 17:00 (5:00 PM)\n"
            f"â€¢ 18:30 (6:30 PM)\n"
            f"â€¢ 16:00 (4:00 PM)\n\n"
            f"Or send:\n"
            f"â€¢ 'off' to disable reminders\n"
            f"â€¢ 'cancel' to go back"
        )
        context.user_data['setting_reminder'] = True
    
    async def process_reminder_setting(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process reminder time setting"""
        text = update.message.text.strip().lower()
        
        if text == 'cancel':
            context.user_data['setting_reminder'] = False
            await update.message.reply_text("âŒ Reminder setup cancelled.")
            return
        
        if text == 'off':
            # Remove all reminder jobs
            current_jobs = context.job_queue.get_jobs_by_name('daily_reminder')
            for job in current_jobs:
                job.schedule_removal()
            
            context.user_data['setting_reminder'] = False
            await update.message.reply_text("ðŸ”• Daily reminders disabled.")
            return
        
        # Try to parse the time
        import re
        time_match = re.match(r'(\d{1,2}):(\d{2})', text)
        
        if not time_match:
            await update.message.reply_text(
                "âŒ Invalid time format.\n\n"
                "Please use HH:MM format (e.g., 17:00)\n"
                "Or send 'cancel'"
            )
            return
        
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            await update.message.reply_text(
                "âŒ Invalid time.\n\n"
                "Hour must be 0-23, minute must be 0-59\n"
                "Send 'cancel' to go back"
            )
            return
        
        # Remove existing reminder jobs
        current_jobs = context.job_queue.get_jobs_by_name('daily_reminder')
        for job in current_jobs:
            job.schedule_removal()
        
        # Schedule new daily reminder
        reminder_time = datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()
        
        context.job_queue.run_daily(
            self.send_daily_reminder,
            time=reminder_time,
            days=(0, 1, 2, 3, 4),  # Monday-Friday only
            chat_id=update.effective_chat.id,
            name='daily_reminder'
        )
        
        self.reminder_time = f"{hour:02d}:{minute:02d}"
        context.user_data['setting_reminder'] = False
        
        # Convert to 12-hour format for display
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        am_pm = "AM" if hour < 12 else "PM"
        
        await update.message.reply_text(
            f"âœ… *Daily Reminder Set!*\n\n"
            f"â° Time: {display_hour}:{minute:02d} {am_pm}\n"
            f"ðŸ“… Days: Monday - Friday\n\n"
            f"You'll receive a reminder to log your hours every weekday at this time."
        )
    
    async def send_daily_reminder(self, context: ContextTypes.DEFAULT_TYPE):
        """Send daily reminder to log hours"""
        # Get today's date
        today = datetime.now()
        
        # Check if already logged today
        activities = self.load_activities()
        week_key = self.get_current_week_key()
        today_str = today.strftime('%Y-%m-%d')
        
        # Check if logged
        already_logged = False
        if week_key in activities and today_str in activities[week_key]:
            if activities[week_key][today_str]:
                already_logged = True
        
        if already_logged:
            message = (
                f"âœ… Great! You've already logged hours for today "
                f"({today.strftime('%A, %B %d')}).\n\n"
                f"Total logged: "
                f"{sum(act.get('hours', 0) for act in activities[week_key][today_str])} hours"
            )
        else:
            message = (
                f"ðŸ”” *Daily Reminder*\n\n"
                f"Don't forget to log your lab hours for today "
                f"({today.strftime('%A, %B %d')})!\n\n"
                f"Just send me a message like:\n"
                f"'Lab work today. 3 hours'\n\n"
                f"Or tap 'ðŸ“ Log Today'"
            )
        
        await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=message
        )
    
    
    async def email_to_mentor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate timesheet and draft email/Teams message"""
        await update.message.reply_text("ðŸ“§ Generating timesheet and drafting message...")
        
        activities = self.load_activities()
        week_key = self.get_current_week_key()
        
        if week_key not in activities or not activities[week_key]:
            await update.message.reply_text("âŒ No activities logged this week!")
            return
        
        week_data = activities[week_key]
        
        try:
            # Generate AI summary
            await update.message.reply_text("ðŸ¤– Generating AI summary...")
            summary = await self.generate_ai_summary(week_data)
            
            # Prepare timesheet data
            timesheet_data = {
                'student_name': self.user_info['name'],
                'gt_id': self.user_info['gt_id'],
                'week_start': week_key,
                'daily_entries': [],
                'weekly_summary': summary
            }
            
            # Process daily entries
            for date in self.get_week_dates(week_key):
                if date in week_data and week_data[date]:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    day_name = date_obj.strftime('%A')
                    
                    # Calculate total hours
                    total_hours = sum(act.get('hours', 0) for act in week_data[date])
                    
                    # Use standard lab hours: 2:30 PM - 5:30 PM
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
            self.pdf_generator.create_timesheet(timesheet_data, output_path)
            
            # Create email draft
            week_date_str = datetime.strptime(week_key, '%Y-%m-%d').strftime('%B %d, %Y')
            
            email_subject = f"Timesheet - {self.user_info['name']} - Week of {week_date_str}"
            
            email_body = f"""Dear Mentor,

Please find attached my timesheet for the week of {week_date_str}.

Weekly Summary:
{summary}

Best regards,
{self.user_info['name']}"""

            teams_message = f"""Hi,

I've submitted my timesheet for the week of {week_date_str}. Here's a summary of what I worked on:

{summary}

Let me know if you need any additional information!

Thanks,
{self.user_info['name']}"""
            
            # Send the PDF first
            await update.message.reply_document(
                document=open(output_path, 'rb'),
                filename=f"Timesheet_{self.user_info['name']}_{week_key}.pdf",
                caption=f"ðŸ“„ Timesheet for week of {week_date_str}"
            )
            
            # Send email draft
            await update.message.reply_text(
                f"ðŸ“§ *EMAIL DRAFT*\n\n"
                f"*Subject:*\n"
                f"`{email_subject}`\n\n"
                f"*Body:*\n"
                f"```\n{email_body}\n```\n\n"
                f"ðŸ‘† Tap to copy! Then attach the PDF above."
            )
            
            # Send Teams draft
            await update.message.reply_text(
                f"ðŸ’¬ *TEAMS MESSAGE DRAFT*\n\n"
                f"```\n{teams_message}\n```\n\n"
                f"ðŸ‘† Tap to copy and send in Teams!"
            )
            
            # Cleanup
            os.remove(output_path)
            
        except Exception as e:
            logger.error(f"Error generating drafts: {e}")
            await update.message.reply_text(f"âŒ Error generating drafts: {str(e)}")
    
    async def generate_ai_summary(self, week_data):
        """Generate AI summary of weekly activities using Claude"""
        # Compile all activities
        all_activities = []
        for date, activities in sorted(week_data.items()):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            day_name = date_obj.strftime('%A')
            for act in activities:
                all_activities.append(f"{day_name}: {act['activity']}")
        
        activities_text = "\n".join(all_activities)
        
        # Generate summary using Claude
        message = self.anthropic_client.messages.create(
            model="claude-sonnet-4-5-20250929",
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
    
    async def generate_timesheet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate the filled PDF timesheet"""
        await update.message.reply_text("â³ Generating your timesheet...")
        
        activities = self.load_activities()
        week_key = self.get_current_week_key()
        
        if week_key not in activities or not activities[week_key]:
            await update.message.reply_text("âŒ No activities logged this week!")
            return
        
        week_data = activities[week_key]
        
        try:
            # Generate AI summary
            await update.message.reply_text("ðŸ¤– Generating AI summary...")
            summary = await self.generate_ai_summary(week_data)
            
            # Prepare timesheet data
            timesheet_data = {
                'student_name': self.user_info['name'],
                'gt_id': self.user_info['gt_id'],
                'week_start': week_key,
                'daily_entries': [],
                'weekly_summary': summary
            }
            
            # Process daily entries
            for date in self.get_week_dates(week_key):
                if date in week_data and week_data[date]:
                    date_obj = datetime.strptime(date, '%Y-%m-%d')
                    day_name = date_obj.strftime('%A')
                    
                    # Calculate total hours
                    total_hours = sum(act.get('hours', 0) for act in week_data[date])
                    
                    # Use standard lab hours: 2:30 PM - 5:30 PM
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
                        'mentor_initials': ''  # To be filled by mentor
                    })
            
            # Generate PDF
            output_path = f"timesheet_{week_key}.pdf"
            self.pdf_generator.create_timesheet(timesheet_data, output_path)
            
            # Send PDF
            await update.message.reply_text("âœ… Timesheet generated!")
            await update.message.reply_document(
                document=open(output_path, 'rb'),
                filename=f"Timesheet_{self.user_info['name']}_{week_key}.pdf",
                caption=f"ðŸ“„ Your timesheet for week of {week_key}\n\n"
                       f"Weekly Summary:\n{summary[:200]}..."
            )
            
            # Cleanup
            os.remove(output_path)
            
        except Exception as e:
            logger.error(f"Error generating timesheet: {e}")
            await update.message.reply_text(f"âŒ Error generating timesheet: {str(e)}")
    
    def run(self):
        """Start the bot"""
        application = Application.builder().token(self.telegram_token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", self.start_command))
        
        # Message handler
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        # Start polling
        logger.info("Bot starting...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    # Load configuration
    if not os.path.exists('config.json'):
        print("Please create config.json with your settings!")
        print("See config.example.json for template")
        exit(1)
    
    with open('config.json', 'r') as f:
        config = json.load(f)
    
    # Create and run bot
    bot = TimesheetBot(
        telegram_token=config['telegram_token'],
        anthropic_api_key=config['anthropic_api_key'],
        user_info=config['user_info']
    )
    
    bot.run()
