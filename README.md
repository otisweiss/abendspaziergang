# Veedelsräume – Raumbörse für Kölner Gruppen und Vereine

Eine nicht kommerzielle, datensparsame Datenbank aller Orte in Köln, die Räume für Vereine,
Chöre, Initiativen und andere Gruppen anbieten. Sie ist nach Zweck, Ausstattung, Zeiten,
Größe, Kosten, Bezirk und Barrierefreiheit filterbar. *(Arbeitstitel)*

- 📄 [Konzept und Recherche zu bestehenden Lösungen](docs/KONZEPT.md)
- 🔒 [Datenschutzkonzept (VVT, TOM, Löschfristen)](docs/DATENSCHUTZ.md)
- ⚖️ [Betrieb als Privatperson – was gilt?](docs/BETRIEB-ALS-PRIVATPERSON.md)

## Funktionen

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
python manage.py demo_daten      # erfundene Beispielorte + Login demo@example.org / demo-passwort-2026
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
| `datenschutz_bereinigen [--dry-run]` | Löschfristen umsetzen (täglich) |
| `demo_daten` | Beispieldaten für Test und Vorschau |

## Technik

Django 5.2 LTS · SQLite oder PostgreSQL · serverseitiges HTML, kein Build-Schritt · Leaflet
lokal eingebunden · Docker Compose mit Caddy.

Kartendaten © OpenStreetMap-Mitwirkende (ODbL). Leaflet © Volodymyr Agafonkin (BSD-2).
