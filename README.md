# Lab Timesheet Web Application 🔬

A modern, user-friendly web application for tracking lab hours and generating professional timesheets. No more Telegram bots or complicated setups!

## ✨ What's Different?

**Before (Telegram Bot):**
- Had to use Telegram
- Complex bot commands
- Not intuitive
- Required running bot 24/7

**Now (Web App):**
- Clean, modern web interface
- Point and click - no commands to remember
- Works on any device with a browser
- Only run when you need it
- Way more user-friendly!

## 🚀 Quick Start (5 Minutes!)

### 1. Install Requirements

```bash
pip install -r requirements_webapp.txt
```

### 2. Add Your Files

Make sure these files are in the same folder:
- ✅ `app.py` (the web server)
- ✅ `pdf_generator.py` (from your project)
- ✅ `Updated_Weekly_Timesheet__2_.pdf` (your template)
- ✅ `config.json` (will be created automatically)

### 3. Start the App

```bash
python app.py
```

### 4. Open Your Browser

Go to: **http://localhost:5000**

That's it! The app is now running on your computer.

## 📱 How to Use

### First Time Setup

1. **Enter Your Information**
   - Fill in your name
   - Fill in your GT ID
   - Click "Save Information"

### Daily Usage

1. **Log Activities**
   - Go to "Current Week" tab
   - Pick the date
   - Enter hours (optional)
   - Describe what you did
   - Click "Add Activity"

2. **View Your Week**
   - See all your activities organized by day
   - See total hours per day
   - Delete activities if you make a mistake

3. **Generate Timesheet**
   - Click "Generate Timesheet" button
   - AI will create a professional summary
   - PDF downloads automatically
   - Submit to your mentor!

### Managing Past Weeks

1. Go to "Past Weeks" tab
2. See all your previous weeks
3. Generate timesheets for any week
4. Delete old weeks you don't need

## 🎯 Features

✅ **Modern Web Interface** - Beautiful, intuitive design  
✅ **Mobile Friendly** - Works on phone, tablet, or computer  
✅ **Smart AI Summaries** - Automatically generates professional weekly reports  
✅ **Easy Activity Tracking** - Log what you did in seconds  
✅ **Week Overview** - See your whole week at a glance  
✅ **PDF Generation** - Creates proper Georgia Tech timesheets  
✅ **Past Weeks** - Access and manage historical data  
✅ **No Account Needed** - Everything stored locally on your computer  

## 📂 File Structure

```
your-folder/
├── app.py                              # Main web server
├── templates/
│   └── index.html                      # Web interface
├── pdf_generator.py                    # PDF creation
├── Updated_Weekly_Timesheet__2_.pdf   # Your template
├── requirements_webapp.txt             # Python packages
├── config.json                         # Auto-created settings
└── lab_activities.json                # Auto-created activity log
```

## 🔧 Configuration

The app creates `config.json` automatically when you save your information:

```json
{
  "anthropic_api_key": "your-key-here",
  "user_info": {
    "name": "Your Name",
    "gt_id": "903123456"
  }
}
```

You'll need to add your Anthropic API key to `config.json` for AI summaries to work.

## 💡 Pro Tips

1. **Log as you go** - Add activities right after lab work
2. **Be specific** - Better descriptions = better AI summaries
3. **Include hours** - Makes timesheets more accurate
4. **Review before generating** - Check your week in the overview
5. **Keep it running** - Leave the terminal window open while using the app

## 🐛 Troubleshooting

**App won't start?**
- Check all files are in the same folder
- Make sure you installed requirements: `pip install -r requirements_webapp.txt`

**Can't generate PDF?**
- Verify `Updated_Weekly_Timesheet__2_.pdf` is in the folder
- Check the filename is exact (including spaces and underscores)

**AI summary not working?**
- Add your Anthropic API key to `config.json`
- Get a free key at: https://console.anthropic.com

**Page won't load?**
- Make sure you're going to http://localhost:5000
- Check the terminal for error messages

## 🆚 Comparison: Bot vs Web App

| Feature | Telegram Bot | Web App |
|---------|-------------|---------|
| Interface | Text commands | Visual, point-and-click |
| Learning Curve | High (memorize commands) | Low (intuitive) |
| Accessibility | Telegram only | Any web browser |
| Always Running | Yes (drains resources) | No (run when needed) |
| Mobile Friendly | Partially | Fully responsive |
| Setup Difficulty | Complex | Simple |
| User Experience | Okay | Excellent |

## 🔒 Privacy & Security

- **All data stored locally** on your computer
- **No external database** - everything in JSON files
- **No account required** - no passwords to remember
- **Your data stays yours** - delete anytime

## 🎓 Perfect For

- Graduate students tracking lab hours
- Research assistants
- Project ENGAGES participants
- Anyone who needs weekly timesheets
- People who want a simple, clean interface

## 📝 Example Workflow

**Monday Morning:**
```
1. Open http://localhost:5000
2. Log: "Cell culture and PCR prep, 3 hours"
3. Close browser
```

**Throughout the week:**
```
- Open app when you finish lab
- Add what you did
- Takes 30 seconds
```

**Friday Afternoon:**
```
1. Open app
2. Review your week
3. Click "Generate Timesheet"
4. Download PDF
5. Email to mentor
6. Done! 🎉
```

## 🚀 Next Steps

Want to make it even better?

1. **Host it online** - Use Heroku, PythonAnywhere, or Replit
2. **Add email** - Auto-send timesheets to your mentor
3. **Add charts** - Visualize your hours over time
4. **Multi-user** - Share with your lab group
5. **Mobile app** - Wrap in Electron or React Native

## 📧 Questions?

The web app uses the same PDF generator as your Telegram bot, so all your timesheets will look identical and professional.

---

**Made with ❤️ for Georgia Tech researchers**

*No more wrestling with bots - just clean, simple timesheet tracking!*
