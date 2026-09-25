# =====================================================================
#  MAIN.PY  —  Raspberry Pi Pico W (MicroPython) → Adafruit IO
# =====================================================================
#  Stuurt elke minuut alle 10 metingen naar Adafruit IO.
#
#  Bestanden op de Pico (via Thonny → Bestand → Opslaan als → Raspberry Pi Pico):
#    main.py      (dit bestand)
#    secrets.py   (wifi + Adafruit gegevens)
#    bme680.py    (driver BME688/BME680, download:
#                  https://github.com/robert-hh/BME680-Micropython → bme680.py)
#
#  AANSLUITINGEN (pas de GPIO-nummers aan in het blok "PINNEN" hieronder):
#    BME688        SDA → GP4   SCL → GP5   VCC → 3V3   GND → GND
#    DS18B20 (×3)  DATA → GP15 (+ 4,7 kΩ weerstand tussen DATA en 3V3)
#                  → buiten, groen dak en gewoon dak op dezelfde draad
#    Windmeter     → GP16 en GND   (reed-schakelaar, telt pulsen)
#    Regenmeter    → GP17 en GND   (kiepbakje, telt pulsen)
#    Windvaan      → GP26 (ADC0) met 10 kΩ weerstand naar 3V3
#  De wind/regen-waarden zijn voor de standaard "weather meter kit"
#  (SparkFun / Misol). Heb je een andere? Pas de FACTOREN aan.
# =====================================================================

import time, network, urequests, machine, onewire, ds18x20, ntptime
from machine import Pin, I2C, ADC
import secrets
from bme680 import BME680_I2C

# ---------- PINNEN ----------
PIN_SDA, PIN_SCL = 4, 5
PIN_ONEWIRE      = 15
PIN_WIND         = 16
PIN_RAIN         = 17
PIN_VANE_ADC     = 26

# ---------- FACTOREN (weather meter kit) ----------
WIND_KMH_PER_HZ = 2.4      # 1 puls per seconde = 2,4 km/u
RAIN_MM_PER_TIP = 0.2794   # 1 kiep = 0,2794 mm

# ---------- FEED KEYS (moeten gelijk zijn aan js/config.js) ----------
FEEDS = {
    "buiten":      "buiten-temp",
    "vocht":       "luchtvochtigheid",
    "druk":        "luchtdruk",
    "gas":         "gasweerstand",
    "wind":        "windsnelheid",
    "windrichting":"windrichting",
    "regen":       "neerslag",
    "bme_temp":    "bme-temp",
    "groen":       "groen-dak",
    "gewoon":      "gewoon-dak",
}

# ---------- DS18B20-ADRESSEN ----------
# Bij de eerste start drukt de Pico de adressen van alle DS18B20's af.
# Warm één sensor op met je hand om te zien welke welke is,
# en plak de adressen dan hieronder. Leeg = volgorde van ontdekken.
DS_BUITEN = None   # bv. b'\x28\xff\x12\x34\x56\x78\x9a\xbc'
DS_GROEN  = None
DS_GEWOON = None

INTERVAL_S = 60    # elke minuut versturen (10 feeds = 10 verzoeken/min, limiet is 30)

led = Pin("LED", Pin.OUT)

# =====================================================================
#  WIFI
# =====================================================================
def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Verbinden met wifi…")
        wlan.connect(secrets.WIFI_SSID, secrets.WIFI_PASS)
        for _ in range(30):
            if wlan.isconnected():
                break
            led.toggle(); time.sleep(0.5)
    if not wlan.isconnected():
        raise RuntimeError("Wifi mislukt: check naam/wachtwoord in secrets.py")
    led.on()
    print("Wifi OK:", wlan.ifconfig()[0])
    try:
        ntptime.settime()          # klok juist zetten (voor 'neerslag vandaag')
    except Exception:
        print("Tijd ophalen mislukt, verder zonder")

# =====================================================================
#  ADAFRUIT IO
# =====================================================================
def send(feed_key, value):
    url = "https://io.adafruit.com/api/v2/{}/feeds/{}/data".format(secrets.AIO_USERNAME, feed_key)
    try:
        r = urequests.post(url, json={"value": value},
                           headers={"X-AIO-Key": secrets.AIO_KEY})
        ok = r.status_code in (200, 201)
        if not ok:
            print("  ✗", feed_key, r.status_code, r.text[:80])
        r.close()
        return ok
    except Exception as e:
        print("  ✗", feed_key, e)
        return False

# =====================================================================
#  SENSOREN
# =====================================================================
# --- BME688 ---
i2c = I2C(0, sda=Pin(PIN_SDA), scl=Pin(PIN_SCL))
bme = BME680_I2C(i2c=i2c)   # adres 0x77; lukt het niet, probeer BME680_I2C(i2c=i2c, address=0x76)

# --- DS18B20 ---
ow = ds18x20.DS18X20(onewire.OneWire(Pin(PIN_ONEWIRE)))
roms = ow.scan()
print("Gevonden DS18B20-sensoren:")
for r in roms:
    print("  ", r)
ds_buiten = DS_BUITEN or (roms[0] if len(roms) > 0 else None)
ds_groen  = DS_GROEN  or (roms[1] if len(roms) > 1 else None)
ds_gewoon = DS_GEWOON or (roms[2] if len(roms) > 2 else None)

def read_ds():
    ow.convert_temp()
    time.sleep_ms(750)
    rd = lambda rom: round(ow.read_temp(rom), 1) if rom else None
    return rd(ds_buiten), rd(ds_groen), rd(ds_gewoon)

# --- Wind en regen: pulsen tellen met interrupts ---
wind_pulses = 0
rain_tips = 0
_last_wind = 0
_last_rain = 0

def wind_irq(pin):
    global wind_pulses, _last_wind
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_wind) > 10:     # ontdenderen
        wind_pulses += 1
        _last_wind = now

def rain_irq(pin):
    global rain_tips, _last_rain
    now = time.ticks_ms()
    if time.ticks_diff(now, _last_rain) > 150:
        rain_tips += 1
        _last_rain = now

Pin(PIN_WIND, Pin.IN, Pin.PULL_UP).irq(trigger=Pin.IRQ_FALLING, handler=wind_irq)
Pin(PIN_RAIN, Pin.IN, Pin.PULL_UP).irq(trigger=Pin.IRQ_FALLING, handler=rain_irq)

# --- Windvaan: spanning → graden ---
vane = ADC(PIN_VANE_ADC)
# (spanning bij 3,3 V met 10 kΩ, graden) — standaard kit. Meet zelf na en pas aan!
VANE_TABLE = [
    (2.53, 0), (1.31, 22.5), (1.49, 45), (0.27, 67.5), (0.30, 90), (0.21, 112.5),
    (0.59, 135), (0.41, 157.5), (0.92, 180), (0.79, 202.5), (2.03, 225), (1.93, 247.5),
    (3.05, 270), (2.67, 292.5), (2.86, 315), (2.26, 337.5),
]
def read_vane():
    volt = vane.read_u16() * 3.3 / 65535
    return min(VANE_TABLE, key=lambda p: abs(p[0] - volt))[1]

# =====================================================================
#  HOOFDLUS
# =====================================================================
connect_wifi()
rain_today = 0.0
current_day = time.localtime()[2]
last = time.ticks_ms()

while True:
    time.sleep(INTERVAL_S)
    try:
        # Tijd sinds vorige meting (voor windsnelheid)
        now = time.ticks_ms()
        seconds = time.ticks_diff(now, last) / 1000
        last = now

        # Pulsen uitlezen en resetten
        irq_state = machine.disable_irq()
        pulses, tips = wind_pulses, rain_tips
        wind_pulses = rain_tips = 0
        machine.enable_irq(irq_state)

        # Neerslag vandaag (reset om middernacht UTC)
        if time.localtime()[2] != current_day:
            current_day = time.localtime()[2]
            rain_today = 0.0
        rain_today += tips * RAIN_MM_PER_TIP

        buiten, groen, gewoon = read_ds()

        values = {
            "buiten":       buiten,
            "vocht":        round(bme.humidity, 1),
            "druk":         round(bme.pressure, 1),          # hPa
            "gas":          round(bme.gas / 1000),           # Ω → kΩ
            "wind":         round(pulses / seconds * WIND_KMH_PER_HZ, 1),
            "windrichting": read_vane(),
            "regen":        round(rain_today, 1),
            "bme_temp":     round(bme.temperature, 1),
            "groen":        groen,
            "gewoon":       gewoon,
        }
        print("Meting:", values)

        # Wifi weg? Opnieuw verbinden
        if not network.WLAN(network.STA_IF).isconnected():
            connect_wifi()

        for name, val in values.items():
            if val is not None:
                send(FEEDS[name], val)
                time.sleep_ms(200)
        led.toggle(); time.sleep_ms(100); led.toggle()

    except Exception as e:
        print("Fout:", e)
