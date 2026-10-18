"""Parse one/two class digits, preserving rank and collapsing repeated digits."""
def parse_labels(raw,allowed,max_labels):
 code=raw.strip()
 if not 1<=len(code)<=max_labels or any(c not in allowed for c in code):
  raise ValueError('Expected one or two allowed class digits')
 return list(dict.fromkeys(code))
