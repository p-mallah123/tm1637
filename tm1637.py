#!/usr/bin/env python3
import subprocess
from time import time, sleep, localtime
from threading import Thread, Event
import RPi.GPIO as GPIO

# RPi.GPIO setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

CLK = 21
DIO = 20

class TM1637:
    I2C_COMM1 = 0x40
    I2C_COMM2 = 0xC0
    I2C_COMM3 = 0x80
    digit_to_segment = [
        0b0111111, 0b0000110, 0b1011011, 0b1001111, 0b1100110,  # 0-4
        0b1101101, 0b1111101, 0b0000111, 0b1111111, 0b1101111]  # 5-9

    def __init__(self, CLK=21, DIO=20, brightness=1.0):
        self.clk = CLK
        self.dio = DIO
        self.brightness = int(brightness * 7)
        
        # RPi.GPIO pin setup (replaces wiringpi2)
        GPIO.setup(self.clk, GPIO.OUT)
        GPIO.setup(self.dio, GPIO.OUT)
        GPIO.output(self.clk, GPIO.LOW)
        GPIO.output(self.dio, GPIO.LOW)
        
        self._clock_thread = None
        self._clock_running = Event()
        self.military_time = True
        self._show_colon = True

    def bit_delay(self):
        sleep(0.001)

    def start(self):
        GPIO.setup(self.dio, GPIO.OUT)
        self.bit_delay()

    def stop(self):
        GPIO.setup(self.dio, GPIO.OUT)
        self.bit_delay()
        GPIO.output(self.clk, GPIO.HIGH)
        self.bit_delay()
        GPIO.setup(self.dio, GPIO.IN)
        self.bit_delay()

    def write_byte(self, b):
        for i in range(8):
            GPIO.output(self.clk, GPIO.LOW)
            self.bit_delay()
            
            # RPi.GPIO equivalent of wiringpi2 logic
            if b & 1:
                GPIO.setup(self.dio, GPIO.OUT)
                GPIO.output(self.dio, GPIO.HIGH)
            else:
                GPIO.setup(self.dio, GPIO.IN)
            
            self.bit_delay()
            GPIO.output(self.clk, GPIO.HIGH)
            self.bit_delay()
            b >>= 1
        
        GPIO.output(self.clk, GPIO.LOW)
        self.bit_delay()
        GPIO.output(self.clk, GPIO.HIGH)
        self.bit_delay()

    def set_segments(self, segments, pos=0):
        self.start()
        self.write_byte(self.I2C_COMM1)
        self.stop()
        
        self.start()
        self.write_byte(self.I2C_COMM2 + pos)
        for seg in segments:
            self.write_byte(seg)
        self.stop()
        
        self.start()
        self.write_byte(self.I2C_COMM3 + self.brightness)
        self.stop()

    def StartClock(self, military_time=True):
        """Start background clock thread"""
        self.military_time = military_time
        self._clock_running.set()
        self._clock_thread = Thread(target=self._clock_loop, daemon=True)
        self._clock_thread.start()
        print("Clock started in background")

    def StopClock(self):
        """Stop background clock"""
        self._clock_running.clear()
        if self._clock_thread:
            self._clock_thread.join(timeout=1)
        print("Clock stopped")

    def ShowDoublepoint(self, show=True):
        """Toggle colon (double point)"""
        self._show_colon = show

    def _clock_loop(self):
        """Background clock display loop"""
        while self._clock_running.is_set():
            t = localtime()
            hour = t.tm_hour % (24 if self.military_time else 12)
            d0 = self.digit_to_segment[hour // 10] if hour // 10 else 0
            d1 = self.digit_to_segment[hour % 10]
            d2 = self.digit_to_segment[t.tm_min // 10]
            d3 = self.digit_to_segment[t.tm_min % 10]
            
            # Blink colon based on ShowDoublepoint setting
            if self._show_colon:
                self.set_segments([d0, 0x80 + d1, d2, d3])  # Colon ON
                sleep(0.5)
                self.set_segments([d0, d1, d2, d3])          # Colon OFF
                sleep(0.5)
            else:
                self.set_segments([d0, d1, d2, d3])
                sleep(1)

    def cleanup(self):
        self.StopClock()
        GPIO.cleanup([self.clk, self.dio])

# Test function
def show_ip_address(tm):
    try:
        ipaddr = subprocess.check_output("hostname -I", shell=True, timeout=1).strip().split(b".")[0]
        tm.set_segments([tm.digit_to_segment[int(x) & 0xf] for x in ipaddr[:4]])
    except:
        pass

if __name__ == "__main__":
    tm = TM1637(CLK, DIO)
    show_ip_address(tm)
    tm.StartClock(military_time=True)
    sleep(10)
    tm.StopClock()
