"""
Generation du collationnement pilote (readback) - phraseologie OACI
===================================================================
A partir des ordres JSON (du pipeline), produit le texte de READBACK que le
pilote prononce : repetition de l'instruction + indicatif en telephonie.
Ex. {AFR1234, ALT, 10000} (avion a FL130) -> "descend flight level one zero zero, air france one two three four".
Donnees standard (chiffres parles, alphabet OACI, indicatifs telephoniques).
"""
import re

WORD = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four",
        "5": "five", "6": "six", "7": "seven", "8": "eight", "9": "niner"}
LETTER = {"A": "alfa", "B": "bravo", "C": "charlie", "D": "delta", "E": "echo",
          "F": "foxtrot", "G": "golf", "H": "hotel", "I": "india", "J": "juliet",
          "K": "kilo", "L": "lima", "M": "mike", "N": "november", "O": "oscar",
          "P": "papa", "Q": "quebec", "R": "romeo", "S": "sierra", "T": "tango",
          "U": "uniform", "V": "victor", "W": "whiskey", "X": "xray", "Y": "yankee", "Z": "zulu"}
CODE2TEL = {"AFR": "air france", "BAW": "speedbird", "DLH": "lufthansa", "RYR": "ryanair",
            "EZY": "easyjet", "KLM": "klm", "AAL": "american", "UAL": "united", "DAL": "delta",
            "SWR": "swiss", "AUA": "austrian", "THY": "turkish", "UAE": "emirates",
            "QTR": "qatari", "CSA": "csa"}


def num_words(s):
    return " ".join(WORD.get(c, c) for c in str(s))


def spell(s):
    return " ".join(LETTER.get(c.upper(), c) for c in str(s) if c.isalnum())


def callsign_telephony(cs):
    m = re.match(r"^([A-Z]{2,3})(\d+)$", cs or "")
    if m and m.group(1) in CODE2TEL:
        return f"{CODE2TEL[m.group(1)]} {num_words(m.group(2))}"
    out = []
    for ch in (cs or ""):
        if ch.isdigit():
            out.append(WORD[ch])
        elif ch.isalpha():
            out.append(LETTER.get(ch.upper(), ch))
    return " ".join(out)


def readback_for_order(o, cur_alt_ft=None):
    a = str(o.get("action", "")).upper()
    if a == "ALT":
        v = int(o.get("value", 0))
        verb = "maintain" if cur_alt_ft is not None and abs(v-cur_alt_ft) < 50 else ("descend" if (cur_alt_ft is not None and v < cur_alt_ft) else "climb")
        return f"{verb} flight level {num_words(str(v // 100).zfill(3))}"
    if a == "HDG":
        return f"heading {num_words(str(int(o.get('value', 0))).zfill(3))}"
    if a == "SPD":
        return f"speed {num_words(int(o.get('value', 0)))} knots"
    if a == "ADDWPT":
        return f"proceed direct {spell(o.get('wpt', ''))}"
    return ""


def pilot_report(ac, fields, station=None):
    """Speak only measured/configured simulator data; absent data stays unavailable."""
    import math
    phrases = []
    for field in fields:
        if station and field == 'cleared_level' and ac.get('sel_alt_ft') is not None and abs(ac['sel_alt_ft']-ac.get('alt_ft', 0)) < 50:
            continue
        key = {'level':'alt_ft', 'cleared_level':'sel_alt_ft', 'heading':'hdg',
               'speed':'cas_kt', 'ground_speed':'gs', 'vertical_speed':'vs_fpm',
               'squawk':'squawk', 'qnh':'qnh', 'type':'type'}.get(field)
        value = ac.get(key) if key else None
        if field in ('level', 'cleared_level') and value is not None:
            if ac.get('level_reference') == 'flight_level':
                phrase = 'flight level ' + num_words(f'{round(value/100):03d}')
            else:
                hundreds = round(value/100)*100
                thousands, rest = divmod(hundreds, 1000)
                phrase = (num_words(thousands)+' thousand ' if thousands else '')
                phrase += (num_words(rest//100)+' hundred ' if rest else '')
                phrase = phrase.strip() + ' feet'
            phrases.append(('cleared ' if field == 'cleared_level' else '') + phrase)
        elif field == 'position' and ac.get('x') is not None and ac.get('y') is not None:
            bearing = round(math.degrees(math.atan2(ac['x'], ac['y']))) % 360
            phrases.append(f'{num_words(round(math.hypot(ac["x"], ac["y"])))} miles bearing {num_words(f"{bearing:03d}")} from {ac.get("position_reference", "sector centre")}')
        elif field == 'route' and ac.get('route_names') and ac.get('actwp', -1) >= 0:
            names = ac['route_names'][ac['actwp']:]
            phrases.append('routing ' + ', '.join(spell(n) for n in names) if names else 'route information unavailable')
        elif value is not None:
            if field == 'heading':
                phrases.append('heading ' + num_words(f'{round(value)%360:03d}'))
            elif field in ('speed', 'ground_speed'):
                phrases.append(('indicated speed ' if field == 'speed' else 'ground speed ') + num_words(round(value)) + ' knots')
            elif field == 'vertical_speed':
                phrases.append(('climbing ' if value > 0 else 'descending ') + num_words(round(abs(value))) + ' feet per minute' if abs(value) >= 50 else 'maintaining level')
            else:
                phrases.append(field + ' ' + (spell(value) if field == 'type' else num_words(value)))
        else:
            phrases.append('unable, ' + ('requested' if field == 'unknown' else field.replace('_', ' ')) + ' information unavailable')
    if station and ac.get('assigned_speed') is not None:
        phrases.append('assigned speed ' + num_words(ac['assigned_speed']) + ' knots')
    return (station + ', ' if station else '') + callsign_telephony(ac['id']) + ', ' + ', '.join(phrases)


def readback_text(orders, cur_alt=None):
    """Collationnement du PREMIER indicatif uniquement : une transmission
    radio s'adresse a un seul aeronef (les ordres d'autres indicatifs dans le
    meme lot ne sont ni melanges ni collationnes avec la mauvaise altitude)."""
    cur_alt = cur_alt or {}
    if not orders:
        return ""
    cs = orders[0].get("callsign", "")
    mine = [o for o in orders if o.get("callsign", "") == cs]
    phr = [p for p in (readback_for_order(o, cur_alt.get(cs)) for o in mine) if p]
    if not phr:
        return ""
    return ", ".join(phr) + ", " + callsign_telephony(cs)


if __name__ == "__main__":
    print(readback_text([{"callsign": "AFR1234", "action": "ALT", "value": 10000}], {"AFR1234": 13000}))
    print(readback_text([{"callsign": "BAW57", "action": "HDG", "value": 180}]))
    print(readback_text([{"callsign": "RYR9", "action": "ALT", "value": 24000}], {"RYR9": 9000}))
