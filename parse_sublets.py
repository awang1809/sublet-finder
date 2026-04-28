"""Parses rental information from raw Whatsapp messages"""
import re
import csv
from pathlib import Path

HEADER_RE = re.compile(
    r'^\u200e?\['
    r'(\d{4}-\d{2}-\d{2}),\s*'           # date
    r'(\d{1,2}:\d{2}:\d{2})[\s\u202f]*'  # time
    r'([AP]M)\]\s+'                      # AM/PM
    r'(.+?):\s?'                         # sender
    r'(.*)$',                            # body (may contain newlines)
    re.S,
)

SYSTEM_RE = re.compile(
    r'(joined using a group link|created this group|end-to-end encrypted'
    r'|changed the group|changed this group|added|removed|left the group'
    r'|You joined|changed their phone number|changed the subject'
    r'|image omitted|sticker omitted|video omitted|GIF omitted|audio omitted'
    r'|document omitted|This message was deleted|deleted this message'
    r'|Missed voice call|Missed video call)',
    re.I,
)

def load_messages(path: Path):
    """Loads messages, grouping into sender, date, time, body and removing system messages"""
    with open(path, newline='', encoding='utf-8') as f:
        raw = f.read()
    chunks = raw.split('\r\n')
    messages = []
    for chunk in chunks:
        m = HEADER_RE.match(chunk)
        if m:
            date, time, ampm, sender, body = m.groups()
            sender = sender.strip().lstrip('~').strip()
            messages.append({
                'date': date,
                'time': f'{time} {ampm}',
                'sender': sender,
                'body': body,
            })
        else:
            if messages:
                messages[-1]['body'] += '\r\n' + chunk
    # Drop system messages
    out = []
    for msg in messages:
        body = msg['body'].strip()
        if not body:
            continue
        if SYSTEM_RE.search(body[:200]) and len(body) < 200:
            continue
        out.append(msg)
    return out

RESIDENCES = [
    ('Brock Commons',                  r'\bbrock'),
    ('Marine Drive',                   r'\bmarine\s*drive\b'),
    ('Thunderbird Residence',          r'\bthunderbird\b'),
    ('Ponderosa Commons',              r'\bponderosa\b'),
    ('Walter Gage',                    r'\bwalter\b'),
    ('Exchange Residence',             r'\bexchange\b'),
    ('Fairview Crescent',              r'\bfairview\b'),
    ('Acadia Park',                    r'\bacadia\b'),
    ('Iona House',                     r'\biona\b'),
    ('KWTQ',                           r'\bkwtq\b'),
    ('Magda Apartments',               r'\bmagda\b'),
    ("St. John's College",             r"\bst\.?\s*john'?s\s*college\b"),
    ('Green College',                  r'\bgreen\s*college\b'),
    ('Nest Residence',                 r'\bthe\s*nest\b'),
]

UNIT_RE = re.compile(
    r'\b(studio)\b'
    r'|\b(\d)\s*[-\s]?(?:bed(?:room)?|br|bdrm|bd)s?\b'
    r'|\b(one|two|three|four|five|six)[\s-]?bedroom\b',
    re.I,
)
WORDTONUM = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6}

RENT_RES = [
    re.compile(r'\$\s?(\d{1,2}[,.]?\d{3})\b'),
    re.compile(
        r'(?<![\d.])(\d{3,4})\s*(?:cad|usd)?\s*(?:/|\s*per\s*)\s*month', re.I),
    re.compile(r'\brent[:\s]*\$?\s?(\d{1,2}[,.]?\d{3})\b', re.I),
    re.compile(r'\bprice[:\s]*\$?\s?(\d{1,2}[,.]?\d{3})\b', re.I),
]

NEGOTIABLE_RE = re.compile(
    r'\bnegotiable\b|\bnegotiate\b|\bopen to offers?\b|\bobo\b', re.I)
NON_NEG_RE = re.compile(
    r'\bnon[-\s]?negotiable\b|\bnot\s*negotiable\b|\bno\s*negotiation\b', re.I)

FEMALE_RE = re.compile(
    r'\bfemale(?:s|\s*only)?\b|\bgirls?\b|\bwomen?\b|\bshe/her\b', re.I)
MALE_RE = re.compile(
    r'\bmales?(?:\s*only)?\b|\bguys?\b|\bboys?\b|\bmen\b|\bhe/him\b', re.I)

MONTHS = ('january|february|march|april|may|june|july|august|september|'
          'october|november|december|jan|feb|mar|apr|jun|jul|aug|sept?|oct|nov|dec')
DATE_RANGE_RES = [
    re.compile(rf'((?:{MONTHS})\.?\s*\d{{0,2}}(?:st|nd|rd|th)?,?\s*\d{{0,4}})'
               rf'\s*(?:-|–|to|until|thru|through)\s*'
               rf'((?:{MONTHS})\.?\s*\d{{0,2}}(?:st|nd|rd|th)?,?\s*\d{{0,4}})', re.I),
    re.compile(rf'\bfrom\s+((?:{MONTHS})\.?\s*\d{{0,2}},?\s*\d{{0,4}})'
               rf'\s*(?:-|–|to|until)\s*((?:{MONTHS})\.?\s*\d{{0,2}},?\s*\d{{0,4}})', re.I),
]
SINGLE_MONTH_RE = re.compile(
    rf'\b(?:{MONTHS})\.?\s*\d{{0,2}}(?:st|nd|rd|th)?,?\s*20\d{{2}}', re.I)

def find_residence(body: str):
    """finds residence"""
    bl = body.lower()
    for canonical, pat in RESIDENCES:
        if re.search(pat, bl, re.I):
            return canonical
    return None

def find_unit(body: str):
    """Return a canonical unit-type label, or None."""
    bedrooms = None
    is_studio = False

    # Iterate matches and pick the first that yields a useful answer.
    for m in UNIT_RE.finditer(body):
        if m.group(1):  # studio /
            is_studio = True
            break
        if m.group(2):  # digit
            n = int(m.group(2))
            if 1 <= n <= 8:
                bedrooms = n
                break
        if m.group(3):  # word
            n = WORDTONUM.get(m.group(3).lower())
            if n:
                bedrooms = n
                break

    if is_studio:
        return 'Studio'
    if bedrooms:
        label = f'{bedrooms}-bedroom'
        return label
    return None

def find_rent(body: str):
    """finds rent"""
    candidates = []
    for rx in RENT_RES:
        for m in rx.finditer(body):
            raw = m.group(1).replace(',', '').replace('.', '')
            try:
                val = int(raw)
            except ValueError:
                continue
            if 300 <= val <= 3000:
                candidates.append(val)
    if not candidates:
        return None
    return min(candidates)

def find_gender(body: str):
    """finds gender eligibility"""
    has_f = bool(FEMALE_RE.search(body))
    has_m = bool(MALE_RE.search(body))
    if has_f and not has_m:
        return 'Female'
    if has_m and not has_f:
        return 'Male'
    if has_f and has_m:
        return 'Any / mixed'
    return ''

def find_negotiable(body: str):
    """finds negotiablility"""
    if NON_NEG_RE.search(body):
        return 'Non-negotiable'
    if NEGOTIABLE_RE.search(body):
        return 'Negotiable'
    return ''

def find_dates(body: str):
    """finds avalaible dates"""
    for rx in DATE_RANGE_RES:
        m = rx.search(body)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            return f'{a} – {b}'
    m = SINGLE_MONTH_RE.search(body)
    if m:
        return m.group(0).strip()
    return ''

def parse(path: Path):
    """parses body"""
    rows = []
    for msg in load_messages(path):
        body = msg['body']
        if not re.search(r'sublet|rent|month|\$', body, re.I):
            continue
        residence = find_residence(body)
        unit = find_unit(body)
        rent = find_rent(body)
        if not (residence and unit and rent):
            continue
        rows.append({
            'date':        msg['date'],
            'sender':      msg['sender'],
            'residence':   residence,
            'unit_type':   unit,
            'rent_cad':    rent,
            'gender':      find_gender(body),
            'negotiable':  find_negotiable(body),
            'rental_dates': find_dates(body),
            'message':     ' '.join(body.split()),  # collapse whitespace
        })
    return rows

def main():
    """main"""
    src = Path(r'data/_chat.txt')
    out = Path(r'data/postings.csv')
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = parse(src)
    fieldnames = ['date', 'sender', 'residence', 'unit_type', 'rent_cad',
                  'gender', 'negotiable', 'rental_dates', 'message']
    with open(out, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f'wrote {len(rows)} rows -> {out}')

if __name__ == '__main__':
    main()
