"""
Loading animation utilities for diskcomp.
Provides simple indicators for long-running operations.
"""

import sys
import time


class QuickSpinner:
    """
    A brief, non-threaded spinner that shows activity without overwhelming the user.
    Shows for just a moment to indicate the system is working.
    """
    
    def __init__(self, message: str = "Loading..."):
        self.message = message
        
    def __enter__(self):
        # Just show a simple working indicator
        sys.stdout.write(f'⠋ {self.message}')
        sys.stdout.flush()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Clear the line and move to next
        sys.stdout.write('\r' + ' ' * (len(self.message) + 5) + '\r')
        sys.stdout.flush()