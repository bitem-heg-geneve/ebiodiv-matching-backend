import logging
import hashlib
import orjson
from typing import Dict, List, Optional, Any

from ebiodiv import server, storage


CONFIG = server.CONFIG

def divide_chunks(l, n):
    for i in range(0, len(l), n): 
        yield l[i:i + n]


def main():
    storage.initialize(CONFIG['database']['url'])
    session = storage.getSession()

    #
    q = session.query(storage.Event).join(storage.User, storage.User.id==storage.Event.userId).join(storage.Occurrence, storage.Occurrence.id==storage.Event.refOccurrenceId)
    events = []

    occurrenceIdSet = set()
    def addToOccurrenceIdSet(occId):
        nonlocal occurrenceIdSet
        occurrenceIdSet.add(occId)
        return occId

    events = [
        {
            'id': event.id,
            'timestamp': event.timestamp,
            'user': {
                'name': event.user.name,
                'orcid': event.user.orcid, 
            },
            'occurrenceId': str(addToOccurrenceIdSet(event.refOccurrenceId)),
            'relations': [
                {
                    'relatedOccurrenceId': str(addToOccurrenceIdSet(r.relatedOccurrenceId)),
                    'decision': r.decision,
                    'is_new_decision': r.isNewDecision,
                }
                for r in event.relations
            ]
        }
        for event in q.all()
    ]

    occurrences = {}
    for occurrenceIdSubSet in divide_chunks(list(occurrenceIdSet), 100):
        r = session.query(storage.Occurrence).where(storage.Occurrence.id.in_(occurrenceIdSubSet)).all()
        for occ in r:
            occ: storage.Occurrence = occ
            occurrences[str(occ.id)] = orjson.loads(occ.data)
            
    results = {
        'events': events,
        'occurrences': occurrences,
    }

    with  open('output.json', 'wb') as f:
        f.write(orjson.dumps(results))


if __name__ == '__main__':
    main()
