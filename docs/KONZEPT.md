# Konzept: Veedelsräume – Raumbörse für Kölner Gruppen und Vereine

*Arbeitstitel. Stand: Oktober 2026.*

## 1. Problem und Ziel

In Köln gibt es viele Räume, die Gruppen nutzen könnten: Bürgerzentren, Pfarrsäle,
Stadtteilbibliotheken, Nachbarschaftstreffs, Vereinsheime, Hinterzimmer von Gaststätten,
Seminarräume von Unternehmen. Viele davon sind kaum bekannt. Gleichzeitig suchen Chöre,
Vereine, Initiativen und Selbsthilfegruppen Orte für Proben, Treffen, Stammtische,
Infoabende oder Vereinsfeiern. Oft wissen sie nicht, wo sie fragen sollen.

**Ziel:** eine zentrale, filterbare Datenbank aller Orte in Köln, die Räume für Gruppen mit
gemeinschaftlichem oder sozialem Zweck anbieten. Das reicht von kostenlos bis kostenpflichtig,
von öffentlich bis privat und von klein bis groß.

**Nicht im Umfang:** Räume für rein private Anlässe (Geburtstage, Hochzeiten, private
Partys). Dafür gibt es kommerzielle Portale.

## 2. Recherche: Gibt es das schon?

| Angebot | Region | Was es ist | Bewertung für Köln |
|---|---|---|---|
| [RaumFinder auf engagiertes.berlin](https://www.berlin.de/sen/kultgz/aktuelles/pressemitteilungen/2026/pressemitteilung.1646135.php) | Berlin | Vom Senat gefördert, umgesetzt von renk. e.V. Etwa 159 Räume (Stand Februar 2026), meist kostenlos, mit Angaben zu Größe, Ausstattung und Barrierefreiheit. Pilotprojekt mit digitalen Schlüsseltresoren. | **Das nächste Vorbild.** Nur für Berlin. |
| [Raumbörse der FöBe München](https://stadt.muenchen.de/service/info/raume-fur-veranstaltungen-des-burgerschaftlichen-engagement/10161870/n0/) | München | Raumliste der Förderstelle für Bürgerschaftliches Engagement. Seit 2020 gibt es zusätzlich einen [Stadtratsauftrag für eine stadtweite Raumbörse](https://risi.muenchen.de/risi/dokument/v/6147500) („Kapazitätsfinder“). | Zeigt: Kommunen sehen den Bedarf. Nur für München. |
| [depot.social](https://kommunal.de/teilen-gute-nachbarschaft) (Stiftung „Ecken wecken“) | Leipzig | Gemeinnützige verleihen Ressourcen, darunter auch Räume. Für Gemeinwohlorganisationen ermäßigt. | Allgemeine Verleihbörse, nicht auf Räume spezialisiert. |
| [spacebase](https://www.spacebase.com/de/cologne/), [raumperle](https://www.raumperle.de/stadt/koeln/), Kleinanzeigen | bundesweit | Kommerzielle Vermittlung von Event- und Tagungsräumen, oft mit Provision. | Gewerblich ausgerichtet, viele private Feiern. Bürgerzentren und Pfarrsäle fehlen meist. |
| [Leerstandsmelder](https://www.wg-gesucht.de/artikel/fuer-mehr-wohnraum-leerstandsmelder-schaffen-online-transparenz) | einzelne Städte | Leerstand sichtbar machen | Anderes Ziel (Leerstand, nicht nutzbare Räume). |
| Stadt Köln: [Kulturorte](https://www.stadt-koeln.de/leben-in-koeln/kultur/koelner-kulturorte/00018/index.html), [FABE / Netzwerk Bürgerengagement](https://www.stadt-koeln.de/artikel/01086/index.html), [Sozialraumkoordination](https://www.stadt-koeln.de/politik-und-verwaltung/stadtentwicklung-stadtplanung/starke-veedel-starkes-koln/uebersicht-sozialraeume) | Köln | Einzelne Seiten zu Kulturorten, Beratung für Engagierte, Koordinationsbüros in 15 Sozialräumen | **Keine zentrale, filterbare Raumdatenbank.** Gute Datenquellen und Partner. |
| Einzelne Bürgerzentren (z. B. [Bürgerzentrum Ehrenfeld](https://www.qultor.de/kulturschaffende/buergerzentrum-ehrenfeld), [bueze.de](https://bueze.de/raeume/)) | Köln | Eigene Raumseiten | Verstreut, jedes Haus einzeln. |

**Ergebnis:** Für Köln habe ich keine stadtweite, nicht kommerzielle Raumbörse für Vereine
und Gruppen gefunden. Auch eine fertige Open-Source-Software genau für diesen Zweck habe ich
nicht gefunden. Berlin (engagiertes.berlin) zeigt, dass das Modell funktioniert. Deshalb:

- **Eigene, schlanke Software bauen**, selbst gehostet, ohne Datenweitergabe an Dritte.
- **Kooperation anfragen** bei FABE / Kölner Netzwerk Bürgerengagement, der Kölner
  Freiwilligen Agentur, den Sozialraumkoordinationen und dem Kulturamt
  (Kulturraummanagement). Das bringt Reichweite und Vertrauen bei den Raumgebern.
- **Kontakt zu renk. e.V. / engagiertes.berlin aufnehmen**, um Erfahrungen auszutauschen
  (Moderation, Haftung, Schlüsselübergabe).

## 3. Zielgruppen und Rollen

| Rolle | Wer | Darf |
|---|---|---|
| **Öffentlichkeit** | alle | Startseite, Erklärung, Statistik (Anzahl Orte je Stadtbezirk), Formular „Ort melden“, Datenschutz, Impressum |
| **Gruppe / Verein** (registriert, vom Betreiberverein geprüft) | Chöre, Vereine, Initiativen, Selbsthilfegruppen, nicht kommerzielle Gruppen mit sozialem Zweck | Orte suchen und filtern, Kontaktwege öffentlicher Orte sehen, nicht öffentliche Orte einzeln oder gesammelt anfragen, Merkliste, eigene Anfragen verfolgen |
| **Raumgeber** | Träger, Vereine, Kirchengemeinden, Gastronomie, Unternehmen, Privatpersonen | Eigenen Eintrag über einen geheimen Bearbeitungslink anlegen, ändern, pausieren und löschen. Öffentlich oder nicht öffentlich listen. Nutzungsanfragen per Mail zusagen oder absagen. Ein Konto ist nicht nötig. |
| **Redaktion** | Team des Betreibervereins | Gruppen prüfen und freischalten, Orte recherchieren und importieren, Listungsanfragen verschicken, Einträge prüfen. Nachrichten zwischen Gruppen und Raumgebern sieht die Redaktion nicht. |

**Betrieb:** Ein Verein betreibt die Plattform und ist Verantwortlicher im Sinne der DSGVO.
Er prüft jede Registrierung, bevor eine Gruppe suchen kann (`GROUP_MANUAL_APPROVAL=true`).

**Warum Zugang erst nach Registrierung?** Raumgeber geben ihre Kontaktwege eher frei, wenn
sie wissen, dass nur geprüfte Gruppen sie sehen. Außerdem schützt das vor Scraping und
Spam. Die Registrierung fragt Art der Gruppe und Nutzungszweck ab und enthält die Zusage,
keine rein privaten Feiern anzufragen.

## 4. Prozess: vom gesammelten zum gelisteten Ort

```
 Recherche                 Listungsanfrage            Bestätigung             Sichtbar
┌──────────────┐   E-Mail mit  ┌─────────────┐  Raumgeber  ┌─────────────┐        ┌──────────┐
│ recherchiert │──Bestätigungs─▶│  angefragt  │──prüft und──▶│  gelistet   │──────▶│ Suche für│
│ (intern)     │   link         │             │  ergänzt    │             │       │ Gruppen  │
└──────┬───────┘                └──────┬──────┘             └──────┬──────┘        └──────────┘
       │                               │ lehnt ab / keine Antwort  │ pausiert / löscht
       │                               ▼                           ▼
       │                        ┌─────────────┐            ┌─────────────┐
       │                        │ abgelehnt   │            │  pausiert   │
       │                        │ (Sperrvermerk, keine      └─────────────┘
       │                        │ erneute Anfrage)
       ▼                        └─────────────┘
 Freiwillige Meldung über das Formular ─▶ E-Mail-Bestätigung (Double-Opt-in) ─▶ Prüfung durch die Redaktion ─▶ gelistet
```

0. **Öffentliche Quellen (sofort sichtbar):** Einrichtungen, die *selbst öffentlich* Räume
   anbieten (z. B. die 14 städtischen und freien Bürgerhäuser und Bürgerzentren), erscheinen
   mit dem Status *aus öffentlicher Quelle*. Gruppen sehen sie mit dem Hinweis „Noch nicht vom
   Ort bestätigt“ und der Quellenangabe. Übernommen werden nur Angaben, die die Einrichtung
   selbst veröffentlicht, ohne Namen von Mitarbeitenden. Für private Orte ist dieser Status
   technisch gesperrt. Stimmt der Ort später zu, wird er *gelistet*. Widerspricht er, wird der
   Eintrag sofort entfernt. Erster Bestand: `data/orte_koeln.json` (18 sichtbar, 7 intern).
1. **Sammeln (Phase 1):** Die Redaktion legt Orte als *recherchiert* an. Dazu gibt es einen
   OSM-Import (OpenStreetMap: Gemeinschaftszentren, soziale Zentren, Bibliotheken,
   Kulturzentren, Jugendzentren) und einen CSV-Import für Handrecherche. Gesammelt werden
   **nur institutionelle Angaben aus öffentlichen Quellen**: Name, Adresse, Träger,
   allgemeine Kontaktadresse und Quelle. Private Personen und Wohnadressen werden nie
   gesammelt. Recherchierte Orte sind **nicht** öffentlich sichtbar.
2. **Listungsanfrage:** Die Redaktion verschickt aus der Verwaltung eine E-Mail an die
   institutionelle Adresse. Die E-Mail enthält einen persönlichen, zeitlich begrenzten Link.
   Darüber prüft und ergänzt der Raumgeber seinen Eintrag (Räume, Ausstattung, Kosten,
   Zeiten) und stimmt der Veröffentlichung zu – oder lehnt ab.
3. **Ablehnen oder keine Antwort:** Bei Ablehnung bleibt nur ein Sperrvermerk (Name und
   Adresse) gespeichert, damit nicht erneut angefragt wird. Kommt keine Antwort, verfällt der
   Link nach 90 Tagen und der Ort ist wieder „recherchiert“. Insgesamt gibt es höchstens zwei
   Anfragen (Erstanfrage und eine Erinnerung). Das System erzwingt diese Grenze.
4. **Freiwillige Meldung:** Über das öffentliche Formular kann jeder Raumgeber einen Ort
   melden. Danach folgen eine E-Mail-Bestätigung (Double-Opt-in) und eine redaktionelle
   Prüfung. Erst dann ist der Ort gelistet.
5. **Aktuell halten:** Alle 6 Monate fragt das System per E-Mail nach, ob das Angebot noch
   stimmt. Ein Klick auf „Ja, alles ist noch aktuell“ genügt. Ohne Antwort folgt nach 3 Wochen
   eine Erinnerung. Nach 6 Wochen wird der Eintrag pausiert, aber nicht gelöscht. Auch eine
   beantwortete Nutzungsanfrage zählt als Bestätigung. Alle Fristen sind einstellbar
   (`FRESHNESS_*`).

### Nicht öffentliche Listung (z. B. private Räume, Wohnzimmerkonzerte)

```
 Gruppe sieht: Titel, Stadtteil, Größe,       Raumgeber bekommt E-Mail      Zusage → nur DIESE Gruppe sieht
 Ausstattung, Zwecke, Kosten, Zeiten     ──▶  mit Anfrage und Link    ──▶  Name, Adresse, Kontakt
 (kein Name, keine Adresse, keine Karte)      (Adresse bleibt verborgen)    Absage/14 Tage ohne Antwort → nichts
```

- **Einzelanfrage:** Die Gruppe fragt einen nicht öffentlichen Ort über ein Formular an
  (Anlass, Termin, Personenzahl, Nachricht, Antwort-Adresse).
- **Sammelanfrage:** Die Gruppe wählt einen Stadtteil oder Bezirk und weitere Filter (z. B.
  „ab 20 Personen, mit Klavier, abends“). Die Anfrage geht an alle passenden nicht
  öffentlichen Orte, höchstens an 10. Jeder Raumgeber bekommt eine eigene Mail und sieht nur
  seine Anfrage. Die Gruppe erfährt nur die Anzahl, bis jemand zusagt.
- **Schutz:** Die Suche findet nicht öffentliche Orte nicht über Name oder Straße. Höchstens 5
  Anfragen pro Gruppe und Tag. Anfragen werden nach 12 Monaten gelöscht, damit endet auch der
  Zugang. Die Redaktion sieht nur Metadaten, nicht die Nachrichten.

## 5. Datenmodell

```
Ort (Venue)
 ├─ Name, Träger/Betreiber, Trägerart (öffentlich · kirchlich · Verein/gemeinnützig ·
 │   Gastronomie · Unternehmen · privat)
 ├─ Adresse, PLZ, Stadtbezirk (9 Kölner Bezirke), Stadtteil, Koordinaten
 ├─ Beschreibung, Webseite
 ├─ Kontaktweg für Anfragen (Funktionsadresse, Telefon, Online-Formular, Hinweise)
 ├─ Sichtbarkeit: öffentlich gelistet · nicht öffentlich (+ Titel ohne Name/Adresse)
 ├─ Bus und Bahn, Barrierefreiheit (stufenlos, Aufzug, WC, Hörhilfe, Behindertenparkplatz)
 ├─ Status (recherchiert · angefragt · aus öffentlicher Quelle · unbestätigt · in Prüfung ·
 │   gelistet · pausiert · abgelehnt)
 ├─ Aktualität: zuletzt bestätigt, Abfrage/Erinnerung gesendet, Grund einer Pause
 ├─ Herkunft (Recherche/OSM/CSV/Formular), Quelle, Datum der Einwilligung
 └─ Räume (1..n)
     ├─ Name, Fläche m², Kapazität (Personen)
     ├─ Kosten: kostenlos · gegen Spende · ermäßigt für Gemeinnützige · kostenpflichtig,
     │   Preishinweis (Freitext)
     ├─ Ausstattung (Mehrfachauswahl): Klavier/Flügel, Beamer, Leinwand, Tonanlage, WLAN,
     │   Küche, Theke/Ausschank, Bestuhlung, Tische, Bühne, Tageslicht, Flipchart/Moderation,
     │   Garderobe, Außenfläche, Parkplätze, Lager/Schrank …
     ├─ Nutzungszwecke (Mehrfachauswahl): Probe (Chor/Musik), Gruppentreffen, Stammtisch,
     │   Infoabend/Vortrag, Workshop/Seminar, Vereinsfeier, Bewegung/Tanz, Konzert/Auftritt,
     │   Selbsthilfe/Beratung, Mitgliederversammlung …
     ├─ Nutzungsrhythmus: einmalig · regelmäßig
     └─ Zeitfenster (n): Wochentag, von, bis   (+ Freitext „nach Absprache“)
Gruppe (GroupProfile, an ein Benutzerkonto gebunden)
 ├─ Name der Gruppe, Art (Verein e.V., Chor/Ensemble, Initiative, Selbsthilfe …)
 ├─ Stadtbezirk (optional), kurze Beschreibung des Zwecks
 └─ Status: offen · freigeschaltet · gesperrt
Listungsanfrage (ListingRequest): Ort, Empfänger-Adresse, gesendet am, Token-Hash, Ablauf, Ergebnis
Nutzungsanfrage (UsageRequest): Ort, Gruppe, Raum, Anlass, Termin, Personen, Nachricht,
  Antwort-Adresse, Sammelanfrage-Kennung, Status (offen · zugesagt · abgesagt · abgelaufen ·
  zurückgezogen), Token-Hash, Ablauf
Merkliste: Gruppe ↔ Ort
```

**Filter in der Suche:** Freitext, Stadtbezirk, Stadtteil, Art der Listung, barrierefreies WC, Nutzungszweck, Ausstattung (alle gewählten
müssen vorhanden sein), Kapazität ab, Kosten (bis höchstens …), Trägerart, barrierefrei,
Wochentag und Uhrzeit („offen am Mittwoch um 19 Uhr“).

**Bewusst nicht im ersten Schritt:** Buchungskalender und Online-Buchung. Viele Häuser haben
eigene Verfahren. Die Plattform vermittelt den **Kontaktweg**, keine Verträge. Das hält die
Haftung und die Menge der verarbeiteten Daten klein. Ein Kalender kann später kommen.

## 6. Barrierefreiheit, Einfache Sprache, Responsivität

- **Ziel WCAG 2.1 AA / BITV 2.0:** Tastaturbedienung, sichtbarer Fokus, Sprunglink, eine
  `h1` pro Seite, Beschriftungen für alle Felder, Pflichtfelder als Text („(Pflicht)“, nicht
  nur Farbe), Fehlerübersicht oben im Formular mit Sprunglinks und Fokus, `aria-invalid` und
  `aria-describedby` an Feldern, Kontraste in hell und dunkel, keine Animationen, Karte nur
  als Zusatz zur Liste. Automatische Tests prüfen Grundstruktur und Beschriftungen.
- **Einfache Sprache:** Alle Texte für Gruppen und Raumgeber sind kurz und aktiv formuliert
  (DIN 8581-1). Zusätzlich gibt es eine eigene Seite in Einfacher Sprache.
- **Anleitungen und FAQ:** Schritt-für-Schritt-Anleitungen für Gruppen und Raumgeber, häufige
  Fragen (Kosten, Versicherung, Schlüssel, GEMA, Gemeinnützigkeit, Datenschutz) und eine
  Erklärung zur Barrierefreiheit mit Feedback-Weg.
- **Responsiv von Anfang an:** Mobil zuerst gestaltet. Menü und Filter klappen auf dem Handy
  ein, Karten sind ganz anklickbar, Tabellen stehen auf schmalen Bildschirmen untereinander,
  Bedienelemente sind mindestens 44 px hoch. Getestet bei 360, 768 und 1280 px ohne
  horizontales Scrollen.
- **Barrierefreiheit der Räume:** Angaben zu stufenlosem Zugang, Aufzug, WC, Hörhilfe und
  Behindertenparkplatz, filterbar.

## 7. Datenschutz von Anfang an (Privacy by Design, Art. 25 DSGVO)

Ausführlich in [DATENSCHUTZ.md](DATENSCHUTZ.md). Zum Betrieb als Privatperson siehe [BETRIEB-ALS-PRIVATPERSON.md](BETRIEB-ALS-PRIVATPERSON.md). Die Kernpunkte:

- **Datenminimierung:** Für Gruppen nur E-Mail, Passwort, Gruppenname, Gruppenart und
  Zweck. Keine Klarnamenpflicht, keine Telefonnummer, kein Geburtsdatum.
- **Raumgeber-Kontakte als Funktionsadressen** (z. B. vermietung@…). Personenbezogene
  Kontaktdaten nur mit ausdrücklicher Einwilligung beim Eintragen.
- **Recherchierte Daten** stammen nur aus öffentlichen, institutionellen Quellen. Sie sind
  nicht öffentlich sichtbar, bis der Raumgeber zustimmt. Für die einmalige Anfrage gilt das
  berechtigte Interesse (Art. 6 Abs. 1 lit. f). Die Veröffentlichung erfolgt nur mit
  Zustimmung.
- **Keine Drittanbieter:** keine Google Fonts, kein CDN, kein Analytics, kein reCAPTCHA
  (stattdessen Honeypot und Rate-Limit). Leaflet ist lokal eingebunden. **Kartenkacheln
  laden erst nach einem Klick** (Zwei-Klick-Lösung), weil dabei die IP-Adresse an den
  Kachelserver geht.
- **Nur technisch notwendige Cookies** (Sitzung, CSRF). Deshalb ist kein Cookie-Banner nötig.
- **Keine IP-Speicherung** in der Anwendung. Das Rate-Limit arbeitet mit gesalzenen,
  kurzlebigen Hashes. Der Reverse Proxy schreibt nur gekürzte IPs in sein Log.
- **Löschfristen automatisch** (`manage.py datenschutz_bereinigen`, täglich per Cron; Nutzungsanfragen nach 12 Monaten):
  unbestätigte Konten nach 7 Tagen, unbestätigte Meldungen nach 14 Tagen, Links aus unbeantworteten
  Anfragen nach 90 Tagen, Konten ohne Anmeldung nach 24 Monaten.
- **Betroffenenrechte zum Selbstbedienen:** Gruppen können ihre Daten exportieren (JSON)
  und ihr Konto löschen. Raumgeber können ihren Eintrag über den Bearbeitungslink löschen.
- **Sicherheit:** Passwörter mit Argon2, Tokens nur als Hash gespeichert, HTTPS erzwungen
  (HSTS), strenge Content-Security-Policy, Sicherheits-Header, Admin nur für das Team.
- **Dokumentation:** Vorlagen für das Verzeichnis von Verarbeitungstätigkeiten, die TOM und
  die Datenschutzerklärung liegen bei. Sie müssen vor dem Start rechtlich geprüft werden.

## 8. Technik

| Baustein | Wahl | Begründung |
|---|---|---|
| Anwendung | Python 3.12+ / Django 5.2 LTS | Benutzerkonten, Formulare, CSRF-Schutz und Verwaltungsoberfläche sind eingebaut. LTS bis April 2028. |
| Datenbank | SQLite (Laptop/klein) oder PostgreSQL (Server) | Umschaltbar über `DATABASE_URL`. |
| Oberfläche | serverseitiges HTML, eigenes CSS, wenig JavaScript | schnell, barrierearm, ohne Build-Kette |
| Karte | Leaflet (lokal) + OSM-Kacheln nach Klick | datensparsam |
| Betrieb | Docker Compose: App (gunicorn) + PostgreSQL + Caddy (automatisches HTTPS) | ein Befehl zum Starten auf dem Server |
| E-Mail | SMTP eines europäischen Anbieters (mit AV-Vertrag) | für Double-Opt-in und Anfragen |

## 9. Umsetzungsplan

| Phase | Inhalt | Status |
|---|---|---|
| 0 | Recherche, Konzept, Datenschutzkonzept | ✅ in diesem Repo |
| 1 | Grundgerüst: Datenmodell, Verwaltung, Importe (OSM/CSV), Suche mit Filtern, Registrierung mit Double-Opt-in, Meldeformular, Bearbeitungslink, Listungsanfragen, Löschfristen, Tests, Docker | ✅ in diesem Repo |
| 1b | Nicht öffentliche Listung mit Einzel- und Sammelanfrage, Aktualitätsabfrage, Orte aus öffentlichen Quellen, Barrierefreiheit, Einfache Sprache, Anleitungen, FAQ, Responsivität, erster echter Bestand (25 Kölner Orte) | ✅ in diesem Repo |
| 2 | Auf dem Server installieren, SMTP einrichten, OSM-Import laufen lassen, weitere Handrecherche (Pfarrsäle, Stadtteilbibliotheken, Jugendzentren, Sozialraumkoordination) | ⏳ nach Anbindung des Servers |
| 3 | Rechtliche Prüfung (Datenschutzerklärung, Impressum, Nutzungsbedingungen), Kooperationspartner ansprechen, erste Anfragewelle (z. B. 50 Orte) | offen |
| 4 | Start mit Pilot-Gruppen, Rückmeldungen einholen | offen |
| 5 | Ideen: Verfügbarkeitskalender, Anfrage direkt über die Plattform (Kontaktformular ohne Offenlegung der Adresse), Mehrsprachigkeit, Leichte Sprache, offene Daten (Export der bestätigten Orte unter offener Lizenz, mit Zustimmung) | offen |

## 10. Offene Fragen

1. **Betreiberverein:** entschieden: ein Verein betreibt und prüft. Name, Anschrift und
   Vorstand fehlen noch für Impressum und Datenschutzerklärung.
2. **Name und Domain:** „Veedelsräume“ ist ein Arbeitstitel.
3. **Freischaltung der Gruppen:** entschieden: der Betreiberverein prüft von Hand
   (`GROUP_MANUAL_APPROVAL=true`, Hinweis-Mail an `MODERATION_EMAILS`).
4. **Gastronomie für Stammtische:** Hinterzimmer von Kneipen sind ausdrücklich erwünscht.
   Sollen sie gleichberechtigt erscheinen oder als eigene Kategorie?
