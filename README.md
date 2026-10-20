# Veedelsräume – Raumbörse für Kölner Gruppen und Vereine

Eine nicht kommerzielle, datensparsame Datenbank aller Orte in Köln, die Räume für Vereine,
Chöre, Initiativen und andere Gruppen anbieten. Sie ist nach Zweck, Ausstattung, Zeiten,
Größe, Kosten, Bezirk und Barrierefreiheit filterbar. *(Arbeitstitel)*

Betrieben von einem Verein, der alle Gruppen vor der Freischaltung prüft.

- 📄 [Konzept und Recherche zu bestehenden Lösungen](docs/KONZEPT.md)
- 🔒 [Datenschutzkonzept (VVT, TOM, Löschfristen)](docs/DATENSCHUTZ.md)
- 🧭 [Anleitung für das Redaktionsteam](docs/ANLEITUNG-REDAKTION.md)
- ⚖️ [Rechtliches zum Betrieb (Privatperson oder Verein)](docs/BETRIEB-ALS-PRIVATPERSON.md)

## Funktionen

- **Echter Startbestand:** 38 Kölner Orte aus öffentlichen Quellen (`data/orte_koeln.json`),
  davon 22 sofort sichtbar mit dem Hinweis „Noch nicht vom Ort bestätigt“ (alle Bürgerhäuser
  und Bürgerzentren der Stadt Köln, Kulturorte, Brauhäuser mit Gruppenräumen, eine Kegelbahn
  mit eigenem Raum, das Maternushaus), 16 intern zum Anfragen (u. a. Kegelbahn-Kneipen,
  Nachbarschaftstreffs).
- **Hilfe „Städtische Räume nutzen“:** Bürgerhäuser, Schulräume (oft kostenlos für Vereine),
  Turnhallen – ausgewertet aus den Ordnungen der Stadt Köln ([Details](docs/STAEDTISCHE-RAEUME.md)).
- **Nicht öffentliche Listung:** z. B. für private Räume oder Wohnzimmerkonzerte. Gruppen sehen
  nur Stadtteil und Raumangaben. Der Raumgeber sagt per Mail zu oder ab. Erst dann sieht die
  Gruppe Name, Adresse und Kontakt.
- **Raumanfragen über eine zentrale Adresse:** mit der Antwort-Adresse der Gruppe als Reply-To.
  **Eine Anfrage pro Termin und Gruppe**; der Termin wird erst nach Absage, Rückzug oder Ablauf
  wieder frei. Die **Reihenanfrage** fragt bis zu 5 passende Orte nacheinander an, nie gleichzeitig.
- **Aktualitätsabfrage:** automatische Mail alle 6 Monate, Erinnerung, Pause ohne Antwort.
- **Barrierefrei, Einfache Sprache, responsiv:** WCAG 2.1 AA als Ziel, Fehlerübersicht,
  Tastaturbedienung, eigene Seite in Einfacher Sprache, Anleitungen, FAQ, mobil zuerst.

- **Sammeln:** OSM-Import (`import_osm`) und CSV-Import (`import_csv`). Gesammelte Orte
  bleiben intern, bis der Raumgeber zustimmt.
- **Listungsanfrage:** In der Verwaltung Orte auswählen und die Aktion „Listungsanfrage
  senden“ starten. Der Raumgeber bekommt einen persönlichen Link, um zu prüfen, zu ergänzen
  und zuzustimmen oder abzulehnen. Höchstens zwei Anfragen pro Ort.
- **Freiwillige Meldung:** Öffentliches Formular „Raum anbieten“ mit Double-Opt-in und
  redaktioneller Prüfung. Ein Konto ist nicht nötig, die Verwaltung läuft über einen
  geheimen Link.
- **Suche für Gruppen:** Nach Registrierung und E-Mail-Bestätigung (optional mit manueller
  Freischaltung). Mit Filtern, Merkliste und Karte (Zwei-Klick).
- **Datenschutz:** Keine Drittanbieter, nur notwendige Cookies, Argon2, gehashte Tokens,
  automatische Löschfristen, Datenexport und Selbstlöschung.

## Schnellstart lokal (Laptop)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1            # E-Mails erscheinen dann in der Konsole
python manage.py migrate
python manage.py createcachetable
python manage.py orte_importieren data/orte_koeln.json   # echte Kölner Orte
python manage.py demo_daten      # Demo-Konto demo@example.org / demo-passwort-2026 + 2 fiktive private Räume
python manage.py createsuperuser # Zugang zur Redaktion unter /verwaltung/
python manage.py runserver
```

Dann http://localhost:8000 öffnen. Tests: `DJANGO_DEBUG=1 python manage.py test`

## Betrieb auf einem Server

```bash
cp .env.example .env    # Domain, geheimen Schlüssel, Datenbank-Passwort und SMTP eintragen
docker compose up -d --build
docker compose exec app python manage.py createsuperuser
docker compose exec app python manage.py import_osm     # Orte aus OpenStreetMap sammeln
```

Caddy holt automatisch ein TLS-Zertifikat, sobald die Domain auf den Server zeigt. Der Dienst
`cron` führt jede Nacht `datenschutz_bereinigen` aus.

## Befehle

| Befehl | Zweck |
|---|---|
| `import_osm [--file x.json] [--dry-run]` | Kandidaten aus OpenStreetMap (Bürgerzentren, Bibliotheken, Kulturzentren, Vereinsheime …) |
| `import_csv datei.csv` | Handrecherche importieren, Vorlage: `docs/vorlage-recherche.csv` |
| `orte_importieren datei.json` | Orte mit Räumen importieren (Status „quelle“ oder „recherchiert“) |
| `datenschutz_bereinigen [--dry-run]` | Löschfristen umsetzen (täglich) |
| `aktualitaet_pruefen` | Aktualitätsabfragen, Erinnerungen, Pausen (täglich) |
| `demo_daten` | Beispieldaten für Test und Vorschau |

## Technik

Django 5.2 LTS · SQLite oder PostgreSQL · serverseitiges HTML, kein Build-Schritt · Leaflet
lokal eingebunden · Docker Compose mit Caddy.

Kartendaten © OpenStreetMap-Mitwirkende (ODbL). Leaflet © Volodymyr Agafonkin (BSD-2).
