from gpiozero import Button
from signal import pause
from picamera2 import Picamera2 

button = Button(17)
picam2 = Picamera2()


picam2.configure(picam2.create_still_configuration()) # Init the camera with no preview screen

def on_button_pressed():

    picam2.start()
    picam2.capture_file("test.jpg")
    picam2.stop()
    print("Photo was captured")

button.when_pressed = on_button_pressed


print("Listening")
pause()
