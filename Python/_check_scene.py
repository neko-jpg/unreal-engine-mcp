import json, urllib.request
req = urllib.request.Request(
    'http://127.0.0.1:8787/objects/list',
    data=json.dumps({'scene_id':'cave_auto_001'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read().decode())
    objects = data.get('data', {}).get('objects', [])
    print('Total objects in scene-syncd:', len(objects))
    for obj in objects:
        name = obj.get('name', '?')
        kind = obj.get('kind', '?')
        tags = obj.get('tags', [])
        print(f"  - {name} | kind={kind} | tags={tags}")
except Exception as e:
    print('Error:', e)
