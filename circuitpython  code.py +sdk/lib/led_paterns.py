# led_patterns.py
# -------------------------
# Define LED error patterns for Raspberry Pi Pico / CircuitPython
# Usage: import led_patterns
#        led_patterns.blink(devled)
#        led_patterns.pattern_fast(devled)
#        led_patterns.pattern_sos(devled)

import time

def blink(devled, delay=0.5):
    """Simple blink: ON -> OFF repeatedly"""
    while True:
        devled.value = 1
        time.sleep(delay)
        devled.value = 0
        time.sleep(delay)

def fast(devled):
    """Fast blink: quick flashes"""
    while True:
        devled.value = 1
        time.sleep(0.1)
        devled.value = 0
        time.sleep(0.1)

def slow(devled):
    """Slow blink: long flashes"""
    while True:
        devled.value = 1
        time.sleep(1)
        devled.value = 0
        time.sleep(1)

def sos(devled):
    """SOS Morse code pattern: ... --- ..."""
    def dot():
        devled.value = 1
        time.sleep(0.2)
        devled.value = 0
        time.sleep(0.2)
    def dash():
        devled.value = 1
        time.sleep(0.6)
        devled.value = 0
        time.sleep(0.2)
    
    while True:
        # S: dot dot dot
        dot(); dot(); dot()
        time.sleep(0.2)
        # O: dash dash dash
        dash(); dash(); dash()
        time.sleep(0.2)
        # S: dot dot dot
        dot(); dot(); dot()
        time.sleep(1)