# Anleitung für das Redaktionsteam des Betreibervereins

Die Verwaltung erreicht ihr unter `/verwaltung/`. Zugang bekommt nur, wer `Redaktion`
(Mitarbeiter-Status) ist. Neue Zugänge legt ein Superuser unter *Benutzerkonten* an.

## Täglich: neue Gruppen prüfen

Ihr bekommt eine Mail „Neue Gruppe wartet auf Freischaltung“, wenn `MODERATION_EMAILS` gesetzt ist.

1. *Gruppen* öffnen und nach Status „Wartet auf Freischaltung“ filtern.
2. Angaben prüfen: Ist es eine nicht kommerzielle Gruppe mit gemeinschaftlichem Zweck? Ist der
   Zweck plausibel? Bei Zweifeln die Gruppe per Mail fragen.
3. Gruppe auswählen, Aktion **„Freischalten und per E-Mail benachrichtigen“** ausführen.
4. Wer gegen die Regeln verstößt, wird mit der Aktion **„Sperren“** gesperrt.

## Gemeldete Orte freigeben

Mail „Neuer Ort zur Prüfung“ → *Orte*, Filter „Zugestimmt, in redaktioneller Prüfung“.

- Angaben kurz prüfen: Passt der Ort? Sind keine persönlichen Daten Dritter in Freitexten?
- Aktion **„Freigeben (gelistet) und Raumgeber benachrichtigen“**.
- Nicht passende Orte: Aktion **„Ablehnen / Sperrvermerk“**. Dem Raumgeber den Grund mitteilen
  (das verlangt der Digital Services Act).

## Orte sammeln und anfragen

| Schritt | So geht's |
|---|---|
| Erster Bestand | `python manage.py orte_importieren data/orte_koeln.json` (läuft beim ersten Start einmal) |
| OpenStreetMap | `python manage.py import_osm` → neue Orte mit Status „Recherchiert“ (unsichtbar) |
| Eigene Recherche | Tabelle nach `docs/vorlage-recherche.csv` füllen → `python manage.py import_csv datei.csv` |
| Sichtbar machen ohne Zustimmung | Nur für Einrichtungen, die **selbst öffentlich Räume anbieten**: Trägerart setzen, Quelle (URL) eintragen, Aktion **„Als ‚aus öffentlicher Quelle‘ sichtbar machen“**. Für private Orte ist das gesperrt. Keine Namen von Mitarbeitenden eintragen. |
| Anfragen | Orte mit E-Mail-Adresse auswählen → Aktion **„Listungsanfrage per E-Mail senden“**. Höchstens zwei Anfragen pro Ort. Lieber in kleinen Wellen (z. B. 20 pro Woche) als alle auf einmal. |
| Widerspruch | Meldet sich ein Ort und möchte nicht gezeigt werden: Aktion **„Ablehnen / Sperrvermerk“**. Sofort erledigen. |

## Aktualität

Das System fragt gelistete Orte alle 6 Monate automatisch und pausiert Einträge ohne Antwort
nach 6 Wochen. In der Ortsliste zeigt die Spalte „Zuletzt vom Raumgeber bestätigt“, wie
aktuell ein Eintrag ist. Pausierte Orte mit Grund „Keine Antwort …“ könnt ihr gelegentlich
telefonisch nachfassen.

## Nutzungsanfragen (nicht öffentliche Orte)

Unter *Nutzungsanfragen* seht ihr nur Status und Zahlen, keine Nachrichten. Das ist Absicht.
Fällt auf, dass eine Gruppe sehr viele Anfragen schickt oder Raumgeber sich beschweren: Gruppe
ansprechen und gegebenenfalls sperren.

## Hinweise auf rechtswidrige Inhalte und Barrieren

Meldungen an die Kontaktadresse im Impressum innerhalb weniger Tage prüfen. Wer einen Eintrag
entfernt, nennt dem Raumgeber den Grund. Hinweise auf Barrieren innerhalb von 2 Wochen
beantworten.

## Automatische Aufgaben (Docker-Dienst `cron`, täglich 3:30 Uhr)

- `datenschutz_bereinigen`: löscht unbestätigte Konten (7 Tage), unbestätigte Meldungen (14 Tage),
  Konten ohne Anmeldung (24 Monate) und Nutzungsanfragen (12 Monate) und beendet abgelaufene
  Anfragen und Links
- `aktualitaet_pruefen`: Aktualitätsabfragen, Erinnerungen, Pausen
