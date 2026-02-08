#!/usr/bin/env python3
"""
Quick start script - Run this to launch the app!
"""

import os
import subprocess
import webbrowser
import time

def main():
    print("🔬 Starting Lab Timesheet Web App...")
    print()
    
    # Check if template exists
    if not os.path.exists('Updated_Weekly_Timesheet__2_.pdf'):
        print("⚠️  WARNING: Template PDF not found!")
        print("   Please download 'Updated_Weekly_Timesheet__2_.pdf'")
        print("   and place it in this folder.")
        print()
        input("Press Enter when ready...")
    
    # Check if config exists
    if not os.path.exists('config.json'):
        print("📝 First time setup detected...")
        print("   Running setup wizard...")
        print()
        subprocess.run(['python', 'setup_webapp.py'])
        print()
    
    print("🚀 Launching web server...")
    print()
    print("=" * 60)
    print("  IMPORTANT: Keep this window open!")
    print("  The app will stop if you close it.")
    print("=" * 60)
    print()
    print("Opening browser in 3 seconds...")
    print("If it doesn't open, go to: http://localhost:5000")
    print()
    
    # Open browser after a delay
    time.sleep(3)
    webbrowser.open('http://localhost:5000')
    
    # Start Flask app
    subprocess.run(['python', 'app.py'])

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print()
        print("👋 Shutting down...")
        print("   Thanks for using Lab Timesheet App!")
