#!/usr/bin/env python3
import subprocess
import asyncio
import functools
import time
from typing import Optional, List
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("macOS Notification MCP")

# Lock to ensure only one notification is processed at a time
notification_lock = asyncio.Lock()
# Track if a notification is in progress
is_notification_in_progress = False
# When the last notification started (timestamp)
last_notification_time = 0
# Minimum time between notifications (in seconds)
MIN_NOTIFICATION_INTERVAL = 0.5

# List of available system sounds on macOS
SYSTEM_SOUNDS = [
    "Basso", "Blow", "Bottle", "Frog", "Funk", "Glass", "Hero", 
    "Morse", "Ping", "Pop", "Purr", "Sosumi", "Submarine", "Tink"
]

# Helper functions
def run_command(cmd: List[str]) -> str:
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"

# Decorator to ensure only one notification runs at a time
def single_notification(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        global is_notification_in_progress, last_notification_time
        
        # Check if a notification is already in progress
        if is_notification_in_progress:
            return "Error: Another notification is already in progress"
        
        # Check if minimum interval has passed since last notification
        current_time = time.time()
        if current_time - last_notification_time < MIN_NOTIFICATION_INTERVAL:
            wait_time = MIN_NOTIFICATION_INTERVAL - (current_time - last_notification_time)
            await asyncio.sleep(wait_time)
        
        # Mark as in progress and update timestamp
        is_notification_in_progress = True
        last_notification_time = time.time()
        
        try:
            # Execute the notification function
            return await func(*args, **kwargs)
        finally:
            # Mark as complete
            is_notification_in_progress = False
    
    return wrapper

# Sound Notification Tool
@mcp.tool()
@single_notification
async def sound_notification(sound_name: str = "Submarine") -> str:
    """
    Play a system sound notification.
    
    Args:
        sound_name: Name of the system sound to play (default: "Submarine")
                   Options: Basso, Blow, Bottle, Frog, Funk, Glass, Hero, 
                   Morse, Ping, Pop, Purr, Sosumi, Submarine, Tink
    
    Returns:
        A message indicating whether the sound was played successfully
    """
    if sound_name not in SYSTEM_SOUNDS:
        return f"Error: Sound '{sound_name}' not found"
    
    cmd = ["afplay", f"/System/Library/Sounds/{sound_name}.aiff"]
    run_command(cmd)
    return "success"

# Banner Notification Tool
@mcp.tool()
@single_notification
async def banner_notification(
    title: str,
    message: str,
    subtitle: Optional[str] = None,
    sound: Optional[bool] = False,
    sound_name: Optional[str] = None
) -> str:
    """
    Display a banner notification on macOS.
    
    Args:
        title: The title of the notification
        message: The main content of the notification
        subtitle: Optional subtitle for the notification
        sound: Whether to play a sound with the notification (default: False)
        sound_name: Optional system sound to play (default: None, uses system default)
    
    Returns:
        A message indicating the notification was sent
    """
    script_parts = [
        'display notification',
        f'"{message}"',
        'with title',
        f'"{title}"'
    ]
    
    if subtitle:
        script_parts.extend(['subtitle', f'"{subtitle}"'])
    
    if sound and sound_name:
        if sound_name in SYSTEM_SOUNDS:
            script_parts.extend(['sound name', f'"{sound_name}"'])
        else:
            return f"Error: Sound '{sound_name}' not found"
    elif sound:
        script_parts.extend(['sound name', '"default"'])
    
    applescript = ' '.join(script_parts)
    cmd = ["osascript", "-e", applescript]
    run_command(cmd)
    
    return "success"

# Speak Notification Tool
@mcp.tool()
@single_notification
async def speak_notification(
    text: str,
    voice: Optional[str] = None,
    rate: Optional[int] = 150,
    volume: Optional[float] = 1.0
) -> str:
    """
    Use macOS text-to-speech to speak a message.
    
    Args:
        text: The text to speak
        voice: Optional voice to use (default: system default)
        rate: Speech rate, words per minute (default: 150)
        volume: Volume level from 0.0 to 1.0 (default: 1.0)
    
    Returns:
        A message indicating the text was spoken
    """
    cmd = ["say"]
    
    if rate is not None:
        cmd.extend(["-r", str(rate)])
    
    if voice is not None:
        cmd.extend(["-v", voice])
    
    # Add volume modifier to the text if needed
    if volume is not None and volume != 1.0:
        # Ensure volume is between 0 and 1
        volume = max(0.0, min(1.0, volume))
        # Add volume modifier directly to text
        text = f"[[volm {volume}]] {text}"
    
    cmd.append(text)
    run_command(cmd)
    
    return "success"

# Get available voices
@mcp.tool()
@single_notification
async def list_available_voices() -> str:
    """
    List all available text-to-speech voices on the system.
    
    Returns:
        A string listing all available voices
    """
    cmd = ["say", "-v", "?"]
    result = run_command(cmd)
    return f"Available voices:\n{result}"

# System info and diagnostic tool
@mcp.tool()
async def test_notification_system() -> str:
    """
    Test the notification system by trying all notification methods.
    
    Returns:
        A diagnostic report of the notification system
    """
    report = []
    
    # Test sound notification
    try:
        sound_result = await sound_notification("Submarine")
        report.append(f"Sound notification: Success - {sound_result}")
    except Exception as e:
        report.append(f"Sound notification: Failed - {str(e)}")
    
    # Test banner notification
    try:
        banner_result = await banner_notification(
            title="Test Notification",
            message="This is a test from macOS Notification MCP",
            sound=True
        )
        report.append(f"Banner notification: Success - {banner_result}")
    except Exception as e:
        report.append(f"Banner notification: Failed - {str(e)}")
    
    # Test speak notification
    try:
        speak_result = await speak_notification(
            text="This is a test of the speech notification system",
            rate=175
        )
        report.append(f"Speak notification: Success - {speak_result}")
    except Exception as e:
        report.append(f"Speak notification: Failed - {str(e)}")
    
    return "\n".join(report)

def main():
    version = "0.1.1"
    
    # Print startup message
    print(f"Starting macOS Notification MCP server v{version}...")
    print(f"Available system sounds: {', '.join(SYSTEM_SOUNDS)}")
    
    # Start the MCP server
    mcp.run()

if __name__ == "__main__":
    main()
