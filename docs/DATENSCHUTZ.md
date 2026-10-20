# Datenschutzkonzept

*Vorlage. Vor dem Start an den tatsächlichen Betrieb (Verantwortlicher, Hoster, E-Mail-Anbieter) anpassen.*

## 1. Grundsätze und wie sie umgesetzt sind

| Grundsatz (Art. 5, 25 DSGVO) | Umsetzung in der Software |
|---|---|
| Datenminimierung | Registrierung nur mit E-Mail, Passwort, Gruppenname, Art und Zweck. Kein Klarname, kein Telefon. Beim OSM-Import werden Telefonnummern bewusst nicht übernommen. |
| Zweckbindung | Kontaktwege der Raumgeber sehen nur freigeschaltete Gruppen. Die Nutzungsbedingungen verbieten Werbung und Weitergabe. |
| Speicherbegrenzung | `manage.py datenschutz_bereinigen` läuft täglich (siehe Löschfristen). |
| Transparenz | Datenschutzhinweise in der Anwendung, Hinweise direkt an den Formularen und in jeder E-Mail. |
| Integrität und Vertraulichkeit | HTTPS mit HSTS, Argon2-Passwörter, Tokens nur als SHA-256-Hash, CSP ohne Drittquellen, CSRF-Schutz. Die Verwaltung ist nur für das Team erreichbar. |
| Privacy by Default | Recherchierte Orte sind unsichtbar. Die Karte lädt nur nach Klick. Es gibt kein Tracking und nur notwendige Cookies. |
| Betroffenenrechte | Gruppen: Datenexport (JSON) und Konto löschen in Selbstbedienung. Raumgeber: Bearbeiten, Pausieren und Entfernen über den Link. |

## 2. Verzeichnis von Verarbeitungstätigkeiten (Art. 30)

| Nr. | Tätigkeit | Betroffene | Daten | Rechtsgrundlage | Empfänger | Löschung |
|---|---|---|---|---|---|---|
| 1 | Betrieb der Webseite | Besucher | IP-Adresse (gekürzt im Log), Zeit, URL | Art. 6 Abs. 1 lit. f | Hoster (AV) | Log 7 Tage |
| 2 | Rate-Limit gegen Missbrauch | Besucher | Täglich gesalzener Hash der IP | Art. 6 Abs. 1 lit. f | – | ≤ 1 Stunde |
| 3 | Konten von Gruppen | Kontaktpersonen der Gruppen | E-Mail, Passwort-Hash, Gruppenangaben, Merkliste, Zeitpunkte | Art. 6 Abs. 1 lit. b | Hoster, E-Mail-Anbieter (AV) | Unbestätigt 7 Tage; nach 24 Monaten ohne Anmeldung; jederzeit selbst |
| 4 | Einträge von Raumgebern | Ansprechpartner der Orte | Angaben zum Ort, Kontaktwege, Verwaltungs-E-Mail, Zustimmung | Art. 6 Abs. 1 lit. a | freigeschaltete Gruppen (nur Kontaktwege) | Unbestätigt 14 Tage; bei Entfernen bleibt nur ein Sperrvermerk |
| 5 | Recherche und Listungsanfrage | Institutionen (Funktionsadressen) | Name, Adresse, Träger, allgemeine Kontaktadresse, Quelle | Art. 6 Abs. 1 lit. f (Interessenabwägung, siehe 3.) | E-Mail-Anbieter (AV) | Bei Ablehnung Sperrvermerk; Link nach 90 Tagen ungültig |
| 5a | Orte aus öffentlichen Quellen (sichtbar, unbestätigt) | Einrichtungen, die selbst öffentlich Räume anbieten | Name, Adresse, Webseite, allgemeine Kontaktadresse, Raumangaben, Quelle – keine Namen von Mitarbeitenden | Art. 6 Abs. 1 lit. f | freigeschaltete Gruppen | Bei Widerspruch sofort; Sperrvermerk |
| 5b | Raumanfragen über die zentrale Anfrage-Adresse | Gruppen, Raumgeber | Anlass, Datum und Uhrzeit, Personenzahl, Nachricht, Antwort-Adresse (als Reply-To), Gruppenname, Status, Platz in einer Reihenanfrage | Art. 6 Abs. 1 lit. b, Einwilligung beim Absenden | Raumgeber (per E-Mail); bei nicht öffentlichen Orten nach Zusage die Kontaktangaben an die Gruppe | 12 Monate nach Erstellung; Link nach Antwort oder 10 Tagen ungültig |
| 5c | Aktualitätsabfrage | Raumgeber | Zeitpunkte von Abfrage, Erinnerung, Bestätigung | Art. 6 Abs. 1 lit. f (aktuelle Daten, Art. 5 Abs. 1 lit. d) | E-Mail-Anbieter (AV) | mit dem Eintrag |
| 6 | Kartenanzeige | Besucher (nach Klick) | IP-Adresse an die OSMF | Art. 6 Abs. 1 lit. a | OpenStreetMap Foundation (UK, Angemessenheitsbeschluss) | bei OSMF |

## 3. Interessenabwägung zur Recherche (Art. 6 Abs. 1 lit. f)

- **Interesse:** Gemeinnützigen Gruppen den Zugang zu Räumen erleichtern. Das ist ein
  nicht kommerzielles, gesellschaftlich erwünschtes Ziel.
- **Erforderlichkeit:** Ohne Recherche bleibt die Datenbank leer, und viele Raumgeber
  wissen nicht, dass es die Plattform gibt.
- **Interessen der Betroffenen:** Erfasst werden nur Angaben, die die Institution selbst
  veröffentlicht hat. Es gibt keine Veröffentlichung ohne Zustimmung, höchstens zwei
  E-Mails, einen Widerspruch mit einem Klick und einen Sperrvermerk gegen erneute Anfragen.
  Daten von Privatpersonen werden **nicht** recherchiert. Private Raumgeber kommen nur
  über die freiwillige Meldung hinein.
- **Ergebnis:** Die Interessen der Betroffenen überwiegen nicht.

## 4. Technische und organisatorische Maßnahmen (TOM)

- **Zutritt und Zugang:** Server bei einem EU-Hoster, SSH nur mit Schlüssel, Admin-Konten mit
  starken Passwörtern. Optional die Verwaltung (`/verwaltung/`) per IP oder Basic-Auth im
  Caddyfile zusätzlich schützen.
- **Zugriff:** Rollen „Redaktion“ (`is_staff`) und „Superuser“. Merklisten von Gruppen und
  Nachrichten in Nutzungsanfragen sieht die Redaktion nicht (nur Metadaten).
- **Schutz privater Adressen:** Nicht öffentliche Orte erscheinen ohne Name, Straße und
  Kartenpunkt. Die Volltextsuche durchsucht deren Name und Straße nicht. Details sieht nur eine
  Gruppe mit Zusage. Pro Gruppe und Termin läuft nur eine Anfrage, Reihenanfragen fragen höchstens 5 Orte nacheinander an, pro Gruppe gibt es höchstens 5
  Anfragen am Tag.
- **Weitergabe:** Nur über TLS. Keine Drittanbieter-Skripte (CSP `default-src 'self'`).
- **Eingabekontrolle:** Zustimmungen werden mit Zeitpunkt und Wortlaut gespeichert, dazu ein
  Protokoll der Listungsanfragen.
- **Verfügbarkeit:** Tägliches verschlüsseltes Backup der Datenbank (z. B. `pg_dump` + `restic`)
  an einen zweiten EU-Standort. Backups rotieren nach 30 Tagen, damit gelöschte Daten auch
  dort verschwinden.
- **Trennung:** Eigene Datenbank nur für diese Anwendung.
- **Updates:** Django-LTS-Sicherheitsupdates zeitnah einspielen (`pip install -U`, neu bauen).

## 5. Checkliste vor dem Start

- [x] Verantwortlichen festlegen: Betreiberverein
- [ ] Vereinsdaten in Impressum und Datenschutzerklärung eintragen (`OPERATOR_NAME`, Anschrift, Vorstand)
- [ ] AV-Verträge mit Hoster und E-Mail-Anbieter abschließen
- [ ] Datenschutzerklärung und Nutzungsbedingungen rechtlich prüfen lassen
- [ ] Backup einrichten und eine Wiederherstellung testen
- [ ] Cron für `datenschutz_bereinigen` prüfen (Docker-Dienst `cron`)
- [ ] Ablauf für Datenpannen festlegen (Meldung an LDI NRW innerhalb von 72 Stunden)
- [ ] Demo-Daten löschen: Beispielorte und Demo-Konto
