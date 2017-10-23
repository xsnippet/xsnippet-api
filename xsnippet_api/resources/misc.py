"""
    xsnippet_api.resources.misc
    ---------------------------

    Various misc stuff that is used internally by other modules of the
    resources package. The module is not exposed from the package.

    :copyright: (c) 2016 The XSnippet Team, see AUTHORS for details
    :license: MIT, see LICENSE for details
"""


def cerberus_errors_to_str(errors):
    """Represent Cerberus' errors as a human readable string.

    Anyway we need to show validation errors to human beings, either via
    API responses or logs. So we need a way to convert Cerberus' dict of
    errors to a string and that's exactly what this function is intended
    to do.

    :param errors: cerberus validation errors
    :type errors: dict

    :return: a human readable representation of validation errors
    :rtype: str
    """
    parts = []
    for name, reasons in errors.items():
        for reason in reasons:
            parts.append('`%s` - %s' % (name, reason))
    return ', '.join(parts)


def try_int(value, base=10):
    """Try to cast input value to integer.

    The function is intended to be used as 'coerce' function in Cerberus
    schema. The main use case is to check some string against integer
    constraints such as min or max value.

    :param value: an object to be converted to int
    :type value: any object

    :param base: a base numeral system to be used
    :type base: int

    :return: either int or value itself
    :rtype: either int or type of value
    """
    try:
        return int(value, base)
    except Exception:
        return value
