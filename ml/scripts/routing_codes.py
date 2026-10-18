"""Parse one/two class digits, preserving rank and collapsing repeated digits."""
def parse_labels(raw,allowed,max_labels):
 code=raw.strip()
 if not 1<=len(code)<=max_labels or any(c not in allowed for c in code):
  raise ValueError('Expected one or two allowed class digits')
 return list(dict.fromkeys(code))


def label_prefix_constraint(label_token_ids, eos_token_ids, prompt_length, max_labels):
    """Only class tokens initially; after a class, another distinct class or EOS."""
    labels = tuple(dict.fromkeys(int(x) for x in label_token_ids))
    eos = tuple(dict.fromkeys(int(x) for x in eos_token_ids))
    if not labels or not eos or max_labels not in (1, 2):
        raise ValueError('Invalid routing token constraints')
    if set(labels) & set(eos):
        raise ValueError('Class tokens must differ from EOS')
    def allowed(batch_id, input_ids):
        generated = [int(x) for x in input_ids[prompt_length:]]
        if not generated:
            return list(labels)
        if len(generated) >= max_labels:
            return list(eos)
        return [x for x in labels if x not in generated] + list(eos)
    return allowed
