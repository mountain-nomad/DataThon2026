"""JSON-schema decoding for timeline arrays; no constraints on observed facts."""
from functools import lru_cache

SCHEMA = {
    'type': 'array', 'minItems': 1,
    'items': {
        'type': 'object',
        'properties': {
            't': {'type': 'number', 'minimum': 0},
            'action': {'type': 'string', 'enum': ['setup', 'client_enter', 'client_leave',
                'receive', 'return', 'inspect', 'counter_load', 'counter_unload',
                'safe_put', 'safe_open', 'safe_close', 'other']},
            'event': {'type': 'string', 'minLength': 1},
            'client': {'type': 'integer', 'minimum': 1},
        },
        'required': ['t', 'action', 'event'], 'additionalProperties': False,
    },
}


def _integration():
    # LMFE 0.11.3 imports the base class from its former Transformers location.
    import transformers.tokenization_utils as legacy
    from transformers.tokenization_utils_base import PreTrainedTokenizerBase
    if not hasattr(legacy, 'PreTrainedTokenizerBase'):
        legacy.PreTrainedTokenizerBase = PreTrainedTokenizerBase
    from lmformatenforcer.integrations.transformers import (
        build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn)
    return build_token_enforcer_tokenizer_data, build_transformers_prefix_allowed_tokens_fn


@lru_cache(maxsize=1)
def tokenizer_data(tokenizer):
    build_data, _ = _integration()
    return build_data(tokenizer)


def prefix_constraint(tokenizer, schema=None, *, force_field_order=False):
    from lmformatenforcer import JsonSchemaParser, CharacterLevelParserConfig
    _, build_prefix = _integration()
    config = CharacterLevelParserConfig()
    config.alphabet += ''.join(chr(i) for i in range(0x0400, 0x0530)) + '—–«»…→'
    config.max_json_array_length = 256
    config.force_json_field_order = force_field_order
    return build_prefix(tokenizer_data(tokenizer), JsonSchemaParser(SCHEMA if schema is None else schema, config=config))


def validate(events):
    from jsonschema import validate as json_validate
    json_validate(events, SCHEMA)
