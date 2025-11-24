#!/usr/bin/env python3
"""
Quick test script to verify Slack integration displays BASE_URL correctly
"""
import sys
import os

# Add the QLTYFivable directory to the path so we can import its settings
sys.path.insert(0, '/Users/eduardo/PycharmProjects/QLTYFivable')
sys.path.insert(0, '/Users/eduardo/PycharmProjects/QLTYFramework')

# Import settings from the test project
import settings

# Set up minimal config
import qlty.config as config
config.CURRENT_PLATFORM = 'chrome'
config.SLACK_REPORTING = True
config.REPORT_ON_FAIL = True

# Import the Slack integration
from qlty.classes.integrations.slack_integration import SlackIntegration

print("=" * 60)
print("Testing Slack Integration - Environment URL Display")
print("=" * 60)

# Create SlackIntegration instance
slack = SlackIntegration()

# Test the _get_environment_url method
print(f"\nCurrent Environment: {settings.PROJECT_CONFIG['ENVIRONMENT']}")
print(f"Environment URL: {slack._get_environment_url()}")

# Create a test payload to see the full message structure
results = {
    'total_testcases': 10,
    'passed_testcases': 8,
    'failed_testcases': 2,
    'passed_percentage': '80%',
    'failed_percentage': '20%'
}

print("\n" + "=" * 60)
print("Creating test Slack payload...")
print("=" * 60)

payload = slack._create_payload(results, "5 minutes", testrail_run_id=None, test_run_id="TEST_RUN_001")

# Find and display the environment section
for block in payload['blocks']:
    if block.get('type') == 'context':
        print("\nContext Block:")
        for element in block.get('elements', []):
            text = element.get('text', '')
            if 'Environment:' in text:
                print(f"  ✓ {text}")
                if 'https://lms.5stage.club/' in text:
                    print("  ✓ SUCCESS: BASE_URL is displayed correctly!")
                else:
                    print("  ✗ WARNING: BASE_URL not found in environment field")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
