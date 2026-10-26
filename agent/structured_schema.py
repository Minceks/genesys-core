"""Local size checks for every OpenAI structured response, before API usage.

Count the serialized tree, including repeated dicts: sharing a Python object
does not deduplicate its contents in JSON. Local $ref definitions do.
"""


class StructuredSchemaError(ValueError):
    """A deterministic schema configuration error cannot be repaired by a model."""


def schema_size(schema):
    totals = {'enumValues': 0, 'objectProperties': 0, 'nameCharacters': 0}

    def visit(value):
        if isinstance(value, dict):
            enums = value.get('enum', [])
            if isinstance(enums, list):
                totals['enumValues'] += len(enums)
                totals['nameCharacters'] += sum(len(item) for item in enums if isinstance(item, str))
            for keyword in ('properties', '$defs', 'definitions'):
                entries = value.get(keyword, {})
                if isinstance(entries, dict):
                    totals['nameCharacters'] += sum(len(name) for name in entries)
                    if keyword == 'properties':
                        totals['objectProperties'] += len(entries)
            if isinstance(value.get('const'), str):
                totals['nameCharacters'] += len(value['const'])
            for keyword, item in value.items():
                if keyword in ('properties', '$defs', 'definitions') and isinstance(item, dict):
                    for subschema in item.values():
                        visit(subschema)
                elif keyword not in ('enum', 'const', 'default', 'examples'):
                    visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(schema)
    return totals


def validate_schema_limits(schema):
    sizes = schema_size(schema)
    for metric, maximum in [('enumValues', 1000), ('objectProperties', 5000), ('nameCharacters', 120000)]:
        if sizes[metric] > maximum:
            raise StructuredSchemaError(
                f'Structured response schema exceeds {metric} limit: {sizes[metric]} > {maximum}. '
                'Repair the shared schema configuration; application source is preserved.')
    return sizes
