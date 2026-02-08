#!/usr/bin/env python3
"""
Quick setup script for Lab Timesheet Web App
"""

import json
import os

def setup():
    print("=" * 60)
    print("  Lab Timesheet Web App - Quick Setup")
    print("=" * 60)
    print()
    
    # Check if config exists
    if os.path.exists('config.json'):
        print("✅ config.json already exists")
        with open('config.json', 'r') as f:
            config = json.load(f)
    else:
        print("Creating config.json...")
        config = {
            "anthropic_api_key": "",
            "user_info": {
                "name": "",
                "gt_id": ""
            }
        }
    
    # Get Anthropic API key if not set
    if not config.get('anthropic_api_key'):
        print()
        print("You'll need an Anthropic API key for AI summaries.")
        print("Get one free at: https://console.anthropic.com")
        print()
        api_key = input("Enter your Anthropic API key (or press Enter to skip): ").strip()
        if api_key:
            config['anthropic_api_key'] = api_key
    
    # Save config
    with open('config.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print()
    print("=" * 60)
    print("✅ Setup complete!")
    print()
    print("To start the app:")
    print("  python app.py")
    print()
    print("Then open your browser to:")
    print("  http://localhost:5000")
    print("=" * 60)

if __name__ == '__main__':
    setup()
