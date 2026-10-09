#!/usr/bin/env python3
"""
Master Automation Script for DoorDash Sign-up
Orchestrates: App opening, ADB forwarding, Phone number processing, Browser clearing, Airplane mode
"""

import subprocess
import time
import sys
import os

# Configuration
DEVICE_ID = "ZA222R7JDX"
PACKAGE_NAME = "com.open.caviar"
APP_OPEN_WAIT = 10  # seconds
ADB_FORWARD_WAIT = 5  # seconds
NUMBERS_PER_CYCLE = 10
AIRPLANE_MODE_DURATION = 2  # seconds
CYCLE_RESTART_WAIT = 2  # seconds

# Color codes for output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


def run_command(command, description, check=True):
    """Execute a shell command and handle errors."""
    try:
        print(f"{BLUE}[CMD]{RESET} {description}")
        print(f"  → {command}")
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if check and result.returncode != 0:
            print(f"{RED}[ERROR]{RESET} {description} failed!")
            print(f"  stderr: {result.stderr}")
            return False
        
        if result.stdout:
            print(f"  output: {result.stdout.strip()}")
        
        print(f"{GREEN}[OK]{RESET} {description}")
        return True
    
    except subprocess.TimeoutExpired:
        print(f"{RED}[TIMEOUT]{RESET} {description} timed out!")
        return False
    except Exception as e:
        print(f"{RED}[EXCEPTION]{RESET} {description}: {e}")
        return False


def open_app():
    """Step 1: Open the com.open.caviar app."""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}STEP 1: Opening {PACKAGE_NAME} app{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    # Open the app
    command = f"adb -s {DEVICE_ID} shell am start -n {PACKAGE_NAME}/{PACKAGE_NAME}.MainActivity"
    if not run_command(command, f"Opening {PACKAGE_NAME}"):
        return False
    
    print(f"{GREEN}⏳ Waiting {APP_OPEN_WAIT} seconds for app to fully load...{RESET}")
    time.sleep(APP_OPEN_WAIT)
    
    return True


def setup_adb_forwarding():
    """Step 2: Setup ADB port forwarding for Chrome DevTools."""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}STEP 2: Setting up ADB port forwarding{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    command = f"adb -s {DEVICE_ID} forward tcp:9222 localabstract:chrome_devtools_remote"
    if not run_command(command, "ADB port forwarding (9222 -> chrome_devtools_remote)"):
        return False
    
    print(f"{GREEN}⏳ Waiting {ADB_FORWARD_WAIT} seconds for connection to stabilize...{RESET}")
    time.sleep(ADB_FORWARD_WAIT)
    
    return True


def run_phone_processing():
    """Step 3: Run nfnc6_Version4.py to process phone numbers."""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}STEP 3: Processing phone numbers{RESET}")
    print(f"{YELLOW}Starting nfnc6_Version4.py - will process {NUMBERS_PER_CYCLE} numbers{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    try:
        # Run the phone processing script
        result = subprocess.run(
            ["python3", "nfnc6_Version4.py"],
            timeout=3600,  # 1 hour timeout
            check=False
        )
        
        if result.returncode != 0:
            print(f"{RED}[WARNING]{RESET} Phone processing script exited with code {result.returncode}")
            # Continue anyway - may have processed some numbers
        else:
            print(f"{GREEN}[OK]{RESET} Phone processing completed")
        
        return True
    
    except subprocess.TimeoutExpired:
        print(f"{RED}[TIMEOUT]{RESET} Phone processing took too long!")
        return False
    except Exception as e:
        print(f"{RED}[EXCEPTION]{RESET} Phone processing failed: {e}")
        return False


def clear_chrome_data():
    """Step 4: Clear Chrome browser data."""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}STEP 4: Clearing Chrome browser data{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    commands = [
        (
            f"adb -s {DEVICE_ID} shell pm clear com.android.chrome",
            "Clearing Chrome app cache and data"
        ),
    ]
    
    for cmd, desc in commands:
        if not run_command(cmd, desc, check=False):
            print(f"{YELLOW}[WARNING]{RESET} {desc} failed, continuing...")
    
    return True


def toggle_airplane_mode():
    """Step 5: Toggle Airplane Mode on/off."""
    print(f"\n{YELLOW}{'='*60}{RESET}")
    print(f"{YELLOW}STEP 5: Toggling Airplane Mode{RESET}")
    print(f"{YELLOW}{'='*60}{RESET}")
    
    # Turn Airplane Mode ON
    print(f"{BLUE}Turning Airplane Mode ON...{RESET}")
    cmd_on_1 = f"adb -s {DEVICE_ID} shell settings put global airplane_mode_on 1"
    cmd_on_2 = f"adb -s {DEVICE_ID} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true"
    
    if not run_command(cmd_on_1, "Setting airplane_mode_on = 1"):
        print(f"{YELLOW}[WARNING]{RESET} Failed to set airplane mode setting")
    
    if not run_command(cmd_on_2, "Broadcasting AIRPLANE_MODE = true"):
        print(f"{YELLOW}[WARNING]{RESET} Failed to broadcast airplane mode")
    
    print(f"{GREEN}✓ Airplane Mode is ON{RESET}")
    print(f"{GREEN}⏳ Waiting {AIRPLANE_MODE_DURATION} seconds...{RESET}")
    time.sleep(AIRPLANE_MODE_DURATION)
    
    # Turn Airplane Mode OFF
    print(f"{BLUE}Turning Airplane Mode OFF...{RESET}")
    cmd_off_1 = f"adb -s {DEVICE_ID} shell settings put global airplane_mode_on 0"
    cmd_off_2 = f"adb -s {DEVICE_ID} shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state false"
    
    if not run_command(cmd_off_1, "Setting airplane_mode_on = 0"):
        print(f"{YELLOW}[WARNING]{RESET} Failed to unset airplane mode setting")
    
    if not run_command(cmd_off_2, "Broadcasting AIRPLANE_MODE = false"):
        print(f"{YELLOW}[WARNING]{RESET} Failed to broadcast airplane mode off")
    
    print(f"{GREEN}✓ Airplane Mode is OFF{RESET}")
    
    return True


def main():
    """Main orchestration loop."""
    cycle_count = 0
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}DoorDash Sign-up Automation - Master Controller{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Package: {PACKAGE_NAME}")
    print(f"Numbers per cycle: {NUMBERS_PER_CYCLE}")
    
    try:
        while True:
            cycle_count += 1
            print(f"\n\n{'#'*60}")
            print(f"# CYCLE {cycle_count}")
            print(f"{'#'*60}\n")
            
            # Step 1: Open app
            if not open_app():
                print(f"{RED}Failed to open app. Retrying...{RESET}")
                time.sleep(5)
                continue
            
            # Step 2: Setup ADB forwarding
            if not setup_adb_forwarding():
                print(f"{RED}Failed to setup ADB forwarding. Retrying...{RESET}")
                time.sleep(5)
                continue
            
            # Step 3: Process phone numbers
            if not run_phone_processing():
                print(f"{RED}Phone processing had issues. Continuing to next steps...{RESET}")
            
            # Step 4: Clear Chrome data
            if not clear_chrome_data():
                print(f"{RED}Failed to clear Chrome data. Continuing...{RESET}")
            
            # Step 5: Toggle Airplane Mode
            if not toggle_airplane_mode():
                print(f"{RED}Failed to toggle Airplane Mode. Continuing...{RESET}")
            
            # Prepare for next cycle
            print(f"\n{YELLOW}⏳ Waiting {CYCLE_RESTART_WAIT} seconds before restarting cycle...{RESET}")
            time.sleep(CYCLE_RESTART_WAIT)
            
            print(f"{GREEN}✓ Cycle {cycle_count} completed successfully!{RESET}")
            print(f"{GREEN}Restarting from Step 1...{RESET}")
    
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[INTERRUPTED]{RESET} User stopped the automation.")
        print(f"Completed cycles: {cycle_count}")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n\n{RED}[FATAL ERROR]{RESET} {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
