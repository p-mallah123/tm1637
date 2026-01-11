#!/usr/bin/env python3
import subprocess
from time import time, sleep, localtime
from threading import Thread, Event
from wiringpi2 import wiringPiSetupGpio, pinMode, digitalRead, digitalWrite, GPIO

wiringPiSetupGpio()
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
        self.brightness = int(brightness * 7)  # Scale 0-1.0 to 0-7
        
        pinMode(self.clk, GPIO.OUTPUT)
        pinMode(self.dio, GPIO.OUTPUT)
        digitalWrite(self.clk, GPIO.LOW)
        digitalWrite(self.dio, GPIO.LOW)
        self._clock_thread = None
        self._clock_running = Event()
        self.military_time = True

    def bit_delay(self):
        sleep(0.001)

    def start(self):
        pinMode(self.dio, GPIO.OUTPUT)
        self.bit_delay()

    def stop(self):
        pinMode(self.dio, GPIO.OUTPUT)
        self.bit_delay()
        pinMode(self.clk, GPIO.OUTPUT)
        digitalWrite(self.clk, GPIO.HIGH)
        self.bit_delay()
        pinMode(self.dio, GPIO.INPUT)
        self.bit_delay()

    def write_byte(self, b):
        for i in range(8):
            digitalWrite(self.clk, GPIO.LOW)
            self.bit_delay()
            pinMode(self.dio, GPIO.OUTPUT if (b & 1) else GPIO.INPUT)
            digitalWrite(self.dio, GPIO.HIGH if (b & 1) else GPIO.LOW)
            self.bit_delay()
            digitalWrite(self.clk, GPIO.HIGH)
            self.bit_delay()
            b >>= 1
        
        digitalWrite(self.clk, GPIO.LOW)
        self.bit_delay()
        digitalWrite(self.clk, GPIO.HIGH)
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

    # NEW METHODS FOR YOUR SCRIPT
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
            
            # Blink colon
            if hasattr(self, '_show_colon') and self._show_colon:
                self.set_segments([d0, 0x80 + d1, d2, d3])  # Colon ON
            else:
                self.set_segments([d0, d1, d2, d3])          # Colon OFF
            sleep(0.5)

    def cleanup(self):
        self.StopClock()
        pinMode(self.clk, GPIO.INPUT)
        pinMode(self.dio, GPIO.INPUT)

# Test functions remain the same
def show_ip_address(tm):
    ipaddr = subprocess.check_output("hostname -I", shell=True, timeout=1).strip().split(b".")[0]
    tm.set_segments([tm.digit_to_segment[int(x) & 0xf] for x in ipaddr[:4]])

if __name__ == "__main__":
    tm = TM1637(CLK, DIO)
    show_ip_address(tm)
    tm.StartClock(military_time=True)
    sleep(10)
    tm.StopClock()
