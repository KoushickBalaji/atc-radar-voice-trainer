"""Mock provider responses in the current interpretation contract."""
import json


def response(text, orders, unresolved=()):
    proposals = []
    for order in orders:
        conditional = order.get('action') == 'MISSED_INSTRUCTION'
        proposals.append(dict(evidence=text, timing='on_missed_approach' if conditional else 'immediate',
                              condition=text if conditional else None, order=order))
    return json.dumps(dict(proposals=proposals, unresolved=list(unresolved)))


def reply(messages, orders):
    return response(messages[-1]["content"], orders)
