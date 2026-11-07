"""Conservative vegetation cloning from a save's native tree models."""
import copy
import random
import uuid
from map_editor import terrain_heights

TREE_TYPES={'Birch':'birch','Pine':'pine','Oak':'oak','Maple':'maple'}

def eligible_tree_templates(world):
    return sorted({e.get('Template') for e in world.get('Entities',[]) if e.get('Template') in TREE_TYPES})

def _occupied_cells(world):
    # Conservative: all entity block origins + all known source areas.
    from map_editor import SOURCE_FOOTPRINT
    occupied=set()
    for entity in world.get('Entities',[]):
        comps=entity.get('Components',{})
        c=comps.get('BlockObject',{}).get('Coordinates')
        if not isinstance(c,dict): continue
        x,y=c['X'],c['Y']
        n=SOURCE_FOOTPRINT.get(entity.get('Template'),1)
        for dx in range(n):
            for dy in range(n):occupied.add((x+dx,y+dy))
    return occupied

def plant_forest(world, rectangle, trees, density=70, seed=0, max_trees=2500):
    """Fill rectangle with clones of native tree templates, skipping occupied origins.

    Does not modify land/soil: trees may not survive unfavorable terrain or water.
    """
    nx,ny,heights=terrain_heights(world)
    x0,y0,x1,y1=map(int,rectangle)
    x0,x1=sorted((x0,x1));y0,y1=sorted((y0,y1))
    if not (0<=x0<=x1<nx and 0<=y0<=y1<ny):raise ValueError('Forest rectangle outside map')
    density=int(density)
    if not 1<=density<=100:raise ValueError('Density must be 1–100%')
    if not trees or any(t not in TREE_TYPES for t in trees):raise ValueError('Select existing tree varieties')
    models={}
    for typ in trees:
        candidates=[e for e in world['Entities'] if e.get('Template')==typ]
        if not candidates:raise ValueError(f'No native model for {typ} in this save')
        # Prefer a living specimen; if none exists, avoid cloning dead trees.
        candidates=[e for e in candidates if not e.get('Components',{}).get('LivingNaturalResource',{}).get('IsDead',False)]
        if not candidates:raise ValueError(f'No living model for {typ} in this save')
        models[typ]=min(candidates,key=lambda e: len(e.get('Components',{})))
    occupied=_occupied_cells(world)
    rng=random.Random(seed)
    candidate_cells=[(x,y) for y in range(y0,y1+1) for x in range(x0,x1+1) if (x,y) not in occupied]
    rng.shuffle(candidate_cells)
    amount=min(max_trees,round(len(candidate_cells)*density/100))
    for i,(x,y) in enumerate(candidate_cells[:amount]):
        typ=trees[i%len(trees)]
        clone=copy.deepcopy(models[typ]);clone['Id']=str(uuid.uuid4())
        clone['Components']['BlockObject']['Coordinates']={'X':x,'Y':y,'Z':int(heights[y*nx+x])}
        comp=clone['Components']
        # Preserve only fields native to the selected model; avoid copying death effects.
        if 'LivingNaturalResource' in comp:comp['LivingNaturalResource']['IsDead']=False
        for k in ['WateredNaturalResource','LivingWaterNaturalResource','ContaminatedNaturalResource']:
            if k in comp and 'DyingProgress' in comp[k]:comp[k]['DyingProgress']=0.0
        world['Entities'].append(clone)
    return amount
