import json, glob, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from clean import process

# Build a map threadid -> raw thread dict from all sources
sources = {}
SC = "/sessions/dazzling-fervent-brahmagupta/mnt/Projects/revlv-ceo-dashboard/data/.scratch"
TR = open("/tmp/gmscratch/trdir.txt").read().strip()

# overflow tool-results files
for f in glob.glob(TR + "/*.txt"):
    try:
        d = json.load(open(f))
        if isinstance(d, dict) and 'id' in d and 'messages' in d:
            sources[d['id']] = d
    except Exception as e:
        pass

# my manual raw files
for f in glob.glob(SC + "/raw*.json"):
    try:
        d = json.load(open(f))
        if isinstance(d, dict) and 'id' in d:
            sources[d['id']] = d  # manual overrides overflow if both exist
    except Exception:
        pass

# also already-built tNN.json (for ones processed individually) -- we will rebuild from sources where possible
order = [l.strip() for l in open("/tmp/gmscratch/order.txt") if l.strip()]
missing = []
objs = []
fallbacks = []
for tid in order:
    if tid in sources:
        obj, fb = process(sources[tid])
        objs.append(obj)
        if fb: fallbacks.append(tid)
    else:
        missing.append(tid)
print("total order:", len(order))
print("built:", len(objs))
print("missing:", missing)
print("fallbacks:", fallbacks)
json.dump(objs, open(SC + "/all_objs.json","w"), ensure_ascii=False, indent=2)
