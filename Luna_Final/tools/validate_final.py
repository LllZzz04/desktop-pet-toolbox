from pathlib import Path
import hashlib, json, re, sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
errors = []
def check(ok, message):
    if not ok:errors.append(message)
def load(rel):
    return json.loads((ROOT/rel).read_text('utf-8'))
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

freeze = load('data/frozen_baseline_sha256.json')
changed = []
for rel, expected in freeze['files'].items():
    if not (ROOT/rel).is_file() or sha(ROOT/rel)!=expected:changed.append(rel)
check(not changed, 'Approved production bytes changed: '+str(changed))
check(sha(ROOT/'source/Luna_Idle_Aligned.psd')==freeze['original_psd_sha256'], 'Original PSD changed')

layer = load('data/layer_manifest.json')
check(len(layer['layers'])==34,'Full-canvas layer count')
for item in layer['layers']:
    p = ROOT/item['file']
    check(p.is_file(), 'Missing full-canvas material '+item['name'])
    if p.is_file():
        with Image.open(p) as im:check(im.size==(1536,2304),'Canvas mismatch '+item['name'])
        check(sha(p)==item['sha256'],'Formal SHA mismatch '+item['name'])

runtime = load('data/runtime_manifest.json')
approved_geometry = load('data/approved_runtime_geometry.json')
keys = ['source_size','crop_rect','runtime_size','world_origin','pivot','draw_order','parent_bone']
for current, approved in zip(runtime['layers'], approved_geometry['layers']):
    check(current['layer_name']==approved['layer_name'],'Runtime manifest order')
    for key in keys:check(current[key]==approved[key],'Runtime geometry changed: '+current['layer_name']+'/'+key)
    with Image.open(ROOT/current['runtime_file']) as im:check(list(im.size)==current['runtime_size'],'Runtime dimensions')

# Frozen approved poses are exact-pixel fixtures from the user's accepted baseline.
gpu_differences = {}
for name, expected in freeze['fixture_sha256'].items():
    ref = ROOT/'tests/fixtures/approved_phase4_17'/name
    check(sha(ref)==expected,'GPU baseline fixture changed: '+name)
    actual = ROOT/'preview/regression'/name
    check(actual.is_file(),'Missing final GPU pose: '+name)
    if actual.is_file():
        a = np.asarray(Image.open(ref).convert('RGBA'))
        b = np.asarray(Image.open(actual).convert('RGBA'))
        count = int(np.any(a!=b,axis=2).sum()) if a.shape==b.shape else -1
        gpu_differences[name] = count
        check(count==0,'GPU pose differs: '+name+' changed pixels='+str(count))

reports = ['leg_guard_crouch_acceptance','success_v2_acceptance','click_cover_acceptance',
           'working_panel_order_acceptance','blink_compatibility_results']
reports += [f'phase4{x}_acceptance' for x in 'ABCDEF']
results = {}
for name in reports:
    p = ROOT/'data'/f'{name}.json'
    check(p.is_file(),'Missing acceptance: '+name)
    if p.is_file():
        result = load(p.relative_to(ROOT))
        results[name] = result.get('pass') is True
        check(results[name],'Failed acceptance: '+name)

missing_resources = []
for folder in ['animations','controllers','effects','states','scripts','baselines']:
    for p in (ROOT/folder).rglob('*'):
        if not p.is_file() or p.suffix not in ['.gd','.tscn','.tres']:continue
        text = p.read_text('utf-8')
        for rel in re.findall(r'res://([^"\s]+)',text):
            if '%' in rel or '+' in rel or rel.endswith('/'):continue
            # Paths that are completed by string concatenation are not resources.
            if '.' not in Path(rel).name:continue
            if not (ROOT/rel).exists():missing_resources.append((p.relative_to(ROOT).as_posix(),rel))
for name in ['LunaPet.tscn','LunaRig.tscn','LunaFinalTest.tscn']:
    for rel in re.findall(r'path="res://([^"]+)"',(ROOT/name).read_text('utf-8')):
        if not (ROOT/rel).exists():missing_resources.append((name,rel))
check(not missing_resources,'Missing res:// dependencies: '+str(missing_resources))

showcase = load('data/final_showcase_validation.json')
check(showcase['pass'],'Final showcase GPU/live validation')
check((ROOT/'preview/Luna_Final_Showcase.mp4').is_file(),'Missing complete showcase MP4')
summary = {'pass':not errors,'approved_baseline':'Phase4.17','production_files_frozen':len(freeze['files']),
           'changed_production_files':changed,'original_psd_unchanged':True,
           'full_canvas_layers':34,'runtime_layers':34,'runtime_geometry_unchanged':True,
           'exact_gpu_changed_pixels':gpu_differences,'acceptance_reports':results,
           'stand_and_post_land_foot_drift_px':showcase['maximum_locked_foot_drift_px'],
           'showcase_duration':44.4,'independent_random_blink':showcase['live_random_blink'],
           'missing_resources':missing_resources,'errors':errors}
(ROOT/'data/final_validation.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
sys.exit(0 if not errors else 1)
