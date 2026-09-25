# Weerstation Richtpunt campus Ninove-Zottegem
Door **Xeno Becaus** en **Thomas Roelandt**

```
[Sensoren] → [Pico W] --wifi--> [Adafruit IO] <--leest-- [Website op GitHub Pages]
```

## Mappen

| Bestand | Wat? | Aanpassen? |
|---|---|---|
| `index.html` | Home: huidig weer + trends (24 u / 7 d / 30 d) | nee |
| `dashboard.html` | Alle live metingen, dak-analyse, systeemstatus | nee |
| `over-ons.html` | Jullie team + uitleg over het project | tekst mag |
| `css/style.css` | Huisstijl (goud #D6AD00 uit het Richtpunt-logo) | optioneel |
| `js/config.js` | 👉 **Koppeling met Adafruit IO (website)** | ✅ JA |
| `js/common.js` | Ophalen van data, demo-modus, iconen | nee |
| `js/home.js`, `js/dashboard.js` | Logica per pagina | nee |
| `pico/secrets.py` | 👉 **Wifi + Adafruit key (Pico)** | ✅ JA |
| `pico/main.py` | Leest alle sensoren en stuurt ze door | pinnen/factoren |

## Stap 1: Adafruit IO (10 feeds, precies de gratis limiet)
Maak op https://io.adafruit.com → **Feeds → New Feed** deze feeds (let op de **Key**):

`buiten-temp` · `luchtvochtigheid` · `luchtdruk` · `gasweerstand` · `windsnelheid`
`windrichting` · `neerslag` · `bme-temp` · `groen-dak` · `gewoon-dak`

Zet elke feed op **Public** (feed → ⚙️ → Privacy → Public), dan heeft de website geen key nodig.

## Stap 2: De Pico W
1. Installeer MicroPython op de Pico W, en de editor **Thonny**.
2. Download `bme680.py` van https://github.com/robert-hh/BME680-Micropython
3. Vul `pico/secrets.py` in.
4. Zet `main.py`, `secrets.py` en `bme680.py` op de Pico.
5. Bij de eerste start zie je de adressen van de DS18B20-sensoren. Vul ze in bovenaan `main.py`
   zodat buiten, groen dak en gewoon dak niet door elkaar lopen.
6. In Adafruit IO moeten nu elke minuut waarden binnenkomen.

## Stap 3: De website
1. Vul in `js/config.js` je `AIO_USERNAME` in. De gele DEMO-balk verdwijnt en je ziet echte data.
2. Test door `index.html` te openen in je browser.

## Stap 4: Online met GitHub Pages
1. Maak een repository op GitHub en upload alles **behalve `pico/secrets.py`**
   (het meegeleverde `.gitignore` houdt dat bestand al tegen als je met git werkt).
2. **Settings → Pages → Branch: main → / (root) → Save**
3. Na ± 1 minuut: `https://JOUWNAAM.github.io/REPONAAM/`

## Problemen?
- **"ontbrekende feeds: …"** op het dashboard → die feed key bestaat niet of staat niet op Public.
- **PICO LINK: NIET ACTIEF** → de Pico heeft al meer dan 5 minuten niets gestuurd (Thonny-console bekijken).
- **Trends leeg** → er is nog geen data in die periode; wacht even na de eerste metingen.
- Browser: **F12 → Console** toont de precieze fout.
