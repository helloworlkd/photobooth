#!/usr/bin/env python

import os, sys, time, RPi.GPIO as GPIO, picamera, pygame, subprocess, math, threading, shutil, traceback
from PIL import Image
from neopixel import *


#--- DECLARATION DES VARIABLES

# CAMERA

total_pics 	= 4 				# Nombre de photos a prendre
capture_delay 	= 2 				# Delai (en s) de capture entre chaque photos
prep_delay 	= 3 				# Delai (en s) de preparation
gif_delay 	= 50 				# Delai (en 1/100 s) entre chaque images du .GIF
restart_delay 	= 1.2 				# Delai (en s) d'affichage image de fin
replay_delay 	= 0.5 				# Delai (en s) d'affichage .GIF
replay_cycles 	= 2 				# Nombre de cycle d'affichage .GIF
high_res_w 	= 1640				# Resolution X de l'image
high_res_h	= 922 				# Resolution Y de l'image
monitor_w 	= 1920    			# Resolution X de l'ecran
monitor_h 	= 1080    			# Resolution Y de l'ecran
offset_x 	= 0 				# Offset X (si besoin)
offset_y 	= 0 				# Offset Y (si besoin)
transform_x 	= monitor_w			#
transform_y 	= monitor_h			#

# NEOPIXEL BOUTON

NEOB_COUNT      = 16      			# Nombre de LED
NEOB_PIN        = 18      			# GPIO PIN
NEOB_FREQ_HZ    = 800000  			# Frequence (= 800khz)
NEOB_DMA        = 10      			# Channel DMA
NEOB_BRIGHTNESS = 255     			# Puissance (de 0 a 255)
NEOB_INVERT     = False   			# Inversement du signal (Si NPN transistor level shift)
NEOB_CHANNEL    = 0				# Channel
NEOB_STRIP      = ws.SK6812W_STRIP		# Type de NEOPIXEL

# BOUTON

btn_pinA 	= 32 				# GPIO BOUTTON A
btn_pinB 	= 11 				# GPIO BOUTTON B

# AUTRES

file_path 		= '/media/usb/'
backup_path		= '/home/pi/backup/'
real_path 		= os.path.dirname(os.path.realpath(__file__))


#--- INITIALISATION

# GPIO

GPIO.setmode(GPIO.BOARD)
GPIO.setup(btn_pinA, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(btn_pinB, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# PYGAME

pygame.mixer.pre_init(44100, -16, 2, 2048)
pygame.init()
pygame.mouse.set_visible(False)
pygame.display.set_mode((monitor_w, monitor_h))
screen = pygame.display.get_surface()
pygame.display.toggle_fullscreen()


#--- FONCTIONS

# ANIMATION LEDS BOUTON NEOPIXEL (SPINNER PROCESSING)

def Rainbow(strip, c1, c2, c3, c4, WaveDelay):

	Position=0
	for i in range (0, (NEOB_COUNT * 2)):
		Position = Position + 1
		for i in range (0, NEOB_COUNT):
			strip.setPixelColor(i, Color(int(math.floor(((math.sin(i+Position) * 127 + 128) / 255) * c1)), int(math.floor(((math.sin(i+Position) * 127 + 128) / 255) * c2)), int(math.floor(((math.sin(i+Position) * 127 + 128) / 255) * c3)), int(math.floor(((math.sin(i+Position) * 127 + 128) / 255) * c4))))
		strip.show()
		time.sleep(WaveDelay)

# ANIMATION LEDS BOUTON NEOPIXEL (FULL WHITE)

def colorWipe(strip, color):

	for i in range(strip.numPixels()):
		strip.setPixelColor(i, color)
		strip.show()

# AJUSTEMENT DES VARIABLES D'AFFICHAGE

def set_dimensions(img_w, img_h):

    global transform_y, transform_x, offset_y, offset_x
    ratio_h = (monitor_w * img_h) / img_w

    if (ratio_h < monitor_h):
        transform_y = ratio_h
        transform_x = monitor_w
        offset_y = (monitor_h - ratio_h) / 2
        offset_x = 0

    elif (ratio_h > monitor_h):
        transform_x = (monitor_h * img_w) / img_h
        transform_y = monitor_h
        offset_x = (monitor_w - transform_x) / 2
        offset_y = 0

    else:
        transform_x = monitor_w
        transform_y = monitor_h
        offset_y = offset_x = 0

# AFFICHAGE D'UNE IMAGE

def show_image(image_path):

	screen.fill( (0,0,0) )
	img = pygame.image.load(image_path)
	img = img.convert()
	set_dimensions(img.get_width(), img.get_height())
	img = pygame.transform.scale(img, (transform_x,transform_y))
	screen.blit(img,(offset_x,offset_y))
	pygame.display.flip()

# NETTOYAGE ECRAN

def clear_screen():

	screen.fill( (0,0,0) )
	pygame.display.flip()

# AFFICHAGE D'UN GROUPE D'IMAGES

def display_pics(jpg_group):

    for i in range(0, replay_cycles):
		for i in range(1, total_pics+1):
			show_image(file_path + jpg_group + "-0" + str(i) + ".jpg")
			time.sleep(replay_delay)

# GENERATION DES THUMBNAILS

def convert(now):

	for x in range(1, total_pics+1):
		imagemagick = "convert " + file_path + now + "-0" + str(x) + ".jpg -resize 40% " + file_path + now + "-0" + str(x) + "-xs.jpg"
		os.system(imagemagick)

# SON - SUCCES

def success_sound():

	pygame.mixer.music.load(real_path + "/success.wav")
	pygame.mixer.music.play()

# SON - SNAP

def snap_sound():

	pygame.mixer.music.load(real_path + "/snap.wav")
	pygame.mixer.music.play()

# SON - BIP

def bip_sound():

	pygame.mixer.music.load(real_path + "/bip.wav")
	pygame.mixer.music.play()

# PHOTOBOOTH

def start_photobooth():

	# STEP 1 - INIT

	colorWipe(strip, Color(0, 0, 0, 0))
	show_image(real_path + "/img/instructions.png")
	time.sleep(prep_delay)
	camera = picamera.PiCamera(resolution=(high_res_w, high_res_h), framerate=30, sensor_mode=2)
	camera.vflip = True
	camera.hflip = True
	camera.color_effects = (128,128)
	camera.iso = 800
	camera.exposure_mode = 'night'
	camera.image_effect = 'film'

	# STEP 2 - CAPTURE

	now = time.strftime("%Y-%m-%d-%H-%M-%S")

	try:

		for i in range(1,total_pics+1):

			camera.stop_preview()
			show_image(real_path + "/img/pose" + str(i) + ".png")
			time.sleep(capture_delay)
			#--- Si besoin d'ajouter un "Watermark" comme par exemple un logo
			# Overlay #img = Image.open(real_path + "/overlay.png")
			# Overlay #pad = Image.new('RGBA', (
			# Overlay #	((img.size[0] + 31) // 32) * 32,
			# Overlay #	((img.size[1] + 15) // 16) * 16,
			# Overlay #	))
			# Overlay #pad.paste(img, (0, 0))
			camera.start_preview()
			# Overlay #o = camera.add_overlay(pad.tobytes(), size=img.size)
			# Overlay #o.alpha = 10
			# Overlay #o.layer = 3
			time.sleep(2)
			snap_sound()
			colorWipe(strip, Color(255, 255, 255, 255))
			filename_usb = file_path + now + '-0' + str(i) + '.jpg'
			camera.capture(filename_usb)
			shutil.copy2(filename_usb, backup_path)
			colorWipe(strip, Color(0, 0, 0, 0))
			clear_screen()
			show_image(real_path + "/img/pose" + str(i+1) + ".png")
			# Overlay #camera.remove_overlay(o)
			if i == total_pics+1:
				break

	finally:
		camera.close()

	# STEP 3 - PROCESSING

	show_image(real_path + "/img/processing.png")

	try:

		process = threading.Thread(target=convert, args=[now])
		process.start()
		while process.is_alive():
			Rainbow(strip, 255, 255, 255, 255, .050)
		else:
			colorWipe(strip, Color(0, 0, 0, 0))

	except Exception, e:
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
		pygame.quit()

	# STEP 4 - GENERATING GIF & END

	display_pics(now)
	show_image(real_path + "/img/finished.png")
	subprocess.Popen("convert -treedepth 4 -colors 256 -loop 0 -delay " + str(gif_delay) + " " + file_path + now + "*-xs.jpg " + file_path + now + ".gif", shell=True)
	subprocess.Popen("montage " + file_path + now + "*xs.jpg -tile 2x2 -geometry 512x288 -border 10 -bordercolor '#f7f7f7' " + file_path + now + "-montage.jpg", shell=True)
	success_sound()
	time.sleep(restart_delay)
	show_image(real_path + "/img/intro.png")
	
#--- PROGRAMME

# INTRODUCTION

strip = Adafruit_NeoPixel(NEOB_COUNT, NEOB_PIN, NEOB_FREQ_HZ, NEOB_DMA, NEOB_INVERT, NEOB_BRIGHTNESS, NEOB_CHANNEL, NEOB_STRIP)
strip.begin()
show_image(real_path + "/img/intro.png")
os.system("rm " + file_path + "*-xs.jpg")

while True:

	colorWipe(strip, Color(255, 255, 255, 255))

	if (GPIO.input(btn_pinA) == True):
		bip_sound()
		start_photobooth()
