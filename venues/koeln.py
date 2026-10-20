"""Kölner Stadtbezirke und Stadtteile (86 Stadtteile in 9 Bezirken)."""

DISTRICTS = [
    ("innenstadt", "1 – Innenstadt"),
    ("rodenkirchen", "2 – Rodenkirchen"),
    ("lindenthal", "3 – Lindenthal"),
    ("ehrenfeld", "4 – Ehrenfeld"),
    ("nippes", "5 – Nippes"),
    ("chorweiler", "6 – Chorweiler"),
    ("porz", "7 – Porz"),
    ("kalk", "8 – Kalk"),
    ("muelheim", "9 – Mülheim"),
]

QUARTERS = {
    "innenstadt": ["Altstadt-Nord", "Altstadt-Süd", "Neustadt-Nord", "Neustadt-Süd", "Deutz"],
    "rodenkirchen": [
        "Bayenthal", "Godorf", "Hahnwald", "Immendorf", "Marienburg", "Meschenich", "Raderberg",
        "Raderthal", "Rodenkirchen", "Rondorf", "Sürth", "Weiß", "Zollstock",
    ],
    "lindenthal": [
        "Braunsfeld", "Junkersdorf", "Klettenberg", "Lindenthal", "Lövenich", "Müngersdorf",
        "Sülz", "Weiden", "Widdersdorf",
    ],
    "ehrenfeld": ["Bickendorf", "Bocklemünd/Mengenich", "Ehrenfeld", "Neuehrenfeld", "Ossendorf", "Vogelsang"],
    "nippes": ["Bilderstöckchen", "Longerich", "Mauenheim", "Niehl", "Nippes", "Riehl", "Weidenpesch"],
    "chorweiler": [
        "Blumenberg", "Chorweiler", "Esch/Auweiler", "Fühlingen", "Heimersdorf", "Lindweiler",
        "Merkenich", "Pesch", "Roggendorf/Thenhoven", "Seeberg", "Volkhoven/Weiler", "Worringen",
    ],
    "porz": [
        "Eil", "Elsdorf", "Ensen", "Finkenberg", "Gremberghoven", "Grengel", "Langel", "Libur",
        "Lind", "Poll", "Porz", "Urbach", "Wahn", "Wahnheide", "Westhoven", "Zündorf",
    ],
    "kalk": ["Brück", "Höhenberg", "Humboldt/Gremberg", "Kalk", "Merheim", "Neubrück", "Ostheim", "Rath/Heumar", "Vingst"],
    "muelheim": ["Buchforst", "Buchheim", "Dellbrück", "Dünnwald", "Flittard", "Höhenhaus", "Holweide", "Mülheim", "Stammheim"],
}

ALL_QUARTERS = sorted(q for qs in QUARTERS.values() for q in qs)

_QUARTER_LOOKUP = {}
for _district, _quarters in QUARTERS.items():
    for _q in _quarters:
        _QUARTER_LOOKUP[_q.lower()] = _district
        for _part in _q.split("/"):
            _QUARTER_LOOKUP.setdefault(_part.lower(), _district)


def district_for_quarter(name):
    """Liefert den Stadtbezirk zu einem Stadtteilnamen oder ''."""
    if not name:
        return ""
    return _QUARTER_LOOKUP.get(name.strip().lower(), "")
