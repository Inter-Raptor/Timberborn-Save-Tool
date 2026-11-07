"""Editeur de sources sur carte Timberborn 1.1, sans dépendance tierce."""
import copy
import uuid
import tkinter as tk
from i18n import tr
from tkinter import ttk, messagebox

SOURCE_FOOTPRINT = {'WaterSource': 1, 'BadwaterSource': 3, 'UndergroundRuins': 1, 'GeothermalField': 1}

SOURCE_TYPES = {
    'WaterSource': ('Source d’eau', '#45b7f2'),
    'BadwaterSource': ('Source contaminée', '#c461d8'),
    'UndergroundRuins': ('Mine de fer (ruines souterraines)', '#edb357'),
    'GeothermalField': ('Champ géothermique', '#f16e4d'),
}


def terrain_heights(world):
    size = world['Singletons']['MapSize']['Size']
    nx, ny = size['X'], size['Y']
    raw = world['Singletons']['TerrainMap']['Voxels']['Array']
    # Terrain stocké par couches z : z*(largeur*hauteur)+y*largeur+x.
    array = bytearray(int(v) for v in raw.split())
    plane = nx * ny
    if len(array) % plane:
        raise ValueError('Format du relief non reconnu.')
    heights = bytearray(plane)
    for z in range(len(array) // plane):
        layer = memoryview(array)[z*plane:(z+1)*plane]
        for i, voxel in enumerate(layer):
            if voxel:
                heights[i] = z + 1
    return nx, ny, heights


def find_sources(world):
    return [e for e in world['Entities'] if e.get('Template') in SOURCE_TYPES and
            isinstance(e.get('Components', {}).get('BlockObject', {}).get('Coordinates'), dict)]


def coords(entity):
    return entity['Components']['BlockObject']['Coordinates']


def occupied_origins(world):
    out = set()
    for ent in world['Entities']:
        c = ent.get('Components', {}).get('BlockObject', {}).get('Coordinates')
        if isinstance(c, dict):
            out.add((c['X'], c['Y']))
    return out


def line_points(x0, y0, x1, y1):
    """Bresenham: toutes les cases d'un segment, dans l'ordre."""
    points=[]
    dx=abs(x1-x0); dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        points.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return points


def footprint(x, y, template):
    n=SOURCE_FOOTPRINT[template]
    return {(x+dx,y+dy) for dx in range(n) for dy in range(n)}


def source_conflicts(world, template, x, y):
    """Contrôle conservateur: surface des sources + origines de bâtiments."""
    nx,ny=(world['Singletons']['MapSize']['Size'][k] for k in ('X','Y'))
    footprint_new=footprint(x,y,template)
    if any(px<0 or py<0 or px>=nx or py>=ny for px,py in footprint_new):
        return 'La surface de la source dépasse les limites de la carte.'
    for e in world['Entities']:
        c=e.get('Components',{}).get('BlockObject',{}).get('Coordinates')
        if not isinstance(c,dict): continue
        ex,ey=c['X'],c['Y']
        if e.get('Template') in SOURCE_TYPES:
            existing=footprint(ex,ey,e['Template'])
            if footprint_new & existing:
                return 'La nouvelle source chevauche une source ou un gisement existant.'
        elif (ex,ey) in footprint_new:
            return 'Une origine de bâtiment se trouve dans la zone choisie.'
    return None


def add_source(world, template, x, y, z, strength=1.0):
    """Retourne une nouvelle entité, en clonant un modèle natif de la partie."""
    if template not in SOURCE_TYPES:
        raise ValueError('Type de source inconnu.')
    nx, ny = (world['Singletons']['MapSize']['Size'][k] for k in ('X', 'Y'))
    if not (0 <= x < nx and 0 <= y < ny and 0 <= z < 128):
        raise ValueError('Coordonnées hors des limites.')
    conflict = source_conflicts(world, template, x, y)
    if conflict: raise ValueError(conflict)
    matches = [e for e in world['Entities'] if e.get('Template') == template]
    if not matches:
        raise ValueError('Aucun modèle de ce type dans cette sauvegarde : ajout désactivé pour éviter un fichier invalide.')
    obj = copy.deepcopy(matches[0])
    obj['Id'] = str(uuid.uuid4())
    obj['Components']['BlockObject']['Coordinates'] = {'X': x, 'Y': y, 'Z': z}
    if template in ('WaterSource', 'BadwaterSource'):
        ws = obj['Components']['WaterSource']
        ws['SpecifiedStrength'] = float(strength)
        # Retour aux valeurs d'activation de l'entité modèle; ne pas fabriquer d'autre composant.
    world['Entities'].append(obj)
    return obj


def remove_source(world, identifier):
    for idx, ent in enumerate(world['Entities']):
        if ent.get('Id') == identifier and ent.get('Template') in SOURCE_TYPES:
            del world['Entities'][idx]
            return True
    return False


class MapEditor(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title('Timberborn Save Tool — '+self.t('source_title'))
        self.geometry('1110x850')
        self.minsize(830, 660)
        self.nx, self.ny, self.heights = terrain_heights(parent.world)
        self.scale = min(3, max(1, int(700/max(self.nx, self.ny))))
        self.xvar = tk.IntVar(value=0)
        self.yvar = tk.IntVar(value=0)
        self.zvar = tk.IntVar(value=0)
        self.strength = tk.StringVar(value='1.0')
        self.mode = tk.StringVar(value='WaterSource')
        self.info = tk.StringVar(value='Clic gauche : sélectionner une case. Clic sur un symbole : sélectionner la source.')
        self.selected_id = None
        self.line_start = None
        self.line_mode = tk.BooleanVar(value=False)
        self.forest_mode=tk.BooleanVar(value=False)
        self.forest_start=None
        self.forest_rect=None
        self.tree_flags={t:tk.BooleanVar(value=(t=='Oak')) for t in ('Birch','Pine','Oak','Maple')}
        self.forest_density=tk.IntVar(value=60)
        self.build_ui()
        self.render()

    def t(self,key,**kw):
        return tr(key,self.parent.lang.get(),**kw)

    def build_ui(self):
        root = tk.Frame(self, bg='#ece3d0', padx=15, pady=13)
        root.pack(fill='both', expand=True)
        tk.Label(root, text=self.t('source_title').upper(), bg='#ece3d0', fg='#493824', font=('Georgia', 17, 'bold')).pack(anchor='w')
        tk.Label(root, text=self.t('source_intro'), bg='#ece3d0', fg='#625b4c', font=('Segoe UI', 10)).pack(anchor='w', pady=(3, 8))
        section = ttk.Frame(root)
        section.pack(fill='both', expand=True)
        panel = ttk.Frame(section)
        panel.pack(side='right', fill='y', padx=(12, 0))
        frame = ttk.Frame(section)
        frame.pack(side='left', fill='both', expand=True)
        self.canvas = tk.Canvas(frame, bg='#252b25', highlightthickness=2, highlightbackground='#6d654e',
                                width=self.nx*self.scale, height=self.ny*self.scale)
        xbar = ttk.Scrollbar(frame, orient='horizontal', command=self.canvas.xview)
        ybar = ttk.Scrollbar(frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=xbar.set, yscrollcommand=ybar.set,
                              scrollregion=(0, 0, self.nx*self.scale, self.ny*self.scale))
        self.canvas.grid(row=0,column=0,sticky='nsew')
        ybar.grid(row=0,column=1,sticky='ns')
        xbar.grid(row=1,column=0,sticky='ew')
        frame.rowconfigure(0,weight=1)
        frame.columnconfigure(0,weight=1)
        self.canvas.bind('<Button-1>', self.click)
        self.canvas.bind('<Motion>', self.motion)
        ttk.Label(panel, text=self.t('place_resource').upper(), font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        for code, (label,color) in SOURCE_TYPES.items():
            ttk.Radiobutton(panel, text=self.t({'WaterSource':'water_source','BadwaterSource':'badwater_source','UndergroundRuins':'iron_mine','GeothermalField':'geothermal'}[code]), value=code, variable=self.mode).pack(anchor='w', pady=2)
        ttk.Separator(panel).pack(fill='x',pady=12)
        ttk.Label(panel,text=self.t('selected_tile'),font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        for name,var in [('X',self.xvar),('Y',self.yvar),('Z (altitude)',self.zvar)]:
            line=ttk.Frame(panel);line.pack(fill='x',pady=3)
            ttk.Label(line,text=name,width=15).pack(side='left')
            ttk.Spinbox(line,textvariable=var,from_=0,to=127 if name.startswith('Z') else max(self.nx,self.ny)-1,width=8).pack(side='right')
        line=ttk.Frame(panel);line.pack(fill='x',pady=(10,3))
        ttk.Label(line,text=self.t('flow'),width=15).pack(side='left')
        ttk.Entry(line,textvariable=self.strength,width=10).pack(side='right')
        ttk.Label(panel,text=self.t('flow_help'),foreground='#777777').pack(anchor='w')
        ttk.Checkbutton(panel,text=self.t('line_mode'),variable=self.line_mode,command=self.toggle_line).pack(anchor='w',pady=(12,2))
        ttk.Label(panel,text=self.t('line_help'),foreground='#777777').pack(anchor='w')
        ttk.Button(panel,text='＋  '+self.t('add_here'),style='Green.TButton',command=self.add).pack(fill='x',pady=(12,6))
        ttk.Button(panel,text='✕  '+self.t('remove_source'),style='Wood.TButton',command=self.delete).pack(fill='x',pady=3)
        ttk.Button(panel,text=self.t('refresh_map'),command=self.render).pack(fill='x',pady=3)
        ttk.Separator(panel).pack(fill='x',pady=12)
        ttk.Label(panel,text=self.t('forest_title'),font=('Segoe UI',11,'bold')).pack(anchor='w')
        ttk.Checkbutton(panel,text=self.t('forest_mode'),variable=self.forest_mode,command=self.toggle_forest).pack(anchor='w',pady=4)
        forest_opts=ttk.Frame(panel);forest_opts.pack(fill='x')
        for typ in ('Birch','Pine','Oak','Maple'):
            ttk.Checkbutton(forest_opts,text=self.t({'Birch':'birch','Pine':'pine','Oak':'oak','Maple':'maple'}[typ]),variable=self.tree_flags[typ]).pack(anchor='w')
        ttk.Label(panel,text=self.t('density')).pack(anchor='w',pady=(7,0))
        ttk.Spinbox(panel,from_=1,to=100,textvariable=self.forest_density,width=8).pack(anchor='w')
        ttk.Button(panel,text=self.t('plant_forest'),style='Green.TButton',command=self.plant_selection).pack(fill='x',pady=(8,2))
        ttk.Label(panel,text=self.t('forest_help'),wraplength=230).pack(anchor='w',pady=4)
        ttk.Separator(panel).pack(fill='x',pady=12)
        ttk.Label(panel,text=self.t('safety'),font=('Segoe UI',11,'bold')).pack(anchor='w')
        ttk.Label(panel,text=self.t('map_warning'),justify='left',wraplength=240).pack(anchor='w',pady=5)
        ttk.Label(root,textvariable=self.info,wraplength=1080).pack(anchor='w',pady=(8,0))

    def pixel_color(self,h):
        # Contraste pour rendre lisible le relief.
        v = max(20, min(218, 37 + h*8))
        return f'#{v:02x}{min(255,v+7):02x}{min(255,v+10):02x}'

    def render(self):
        # Image de base 256², agrandie sans interpolation pour une grille pixel précise.
        self.canvas.delete('all')
        img=tk.PhotoImage(width=self.nx,height=self.ny)
        palette=[self.pixel_color(i) for i in range(128)]
        for y in range(self.ny):
            row=' '.join(palette[self.heights[(self.ny-1-y)*self.nx+x]] for x in range(self.nx))
            img.put('{'+row+'}',to=(0,y))
        self.base = img.zoom(self.scale,self.scale)
        self.canvas.create_image(0,0,anchor='nw',image=self.base)
        for ent in find_sources(self.parent.world):
            c=coords(ent); t=ent['Template']; col=SOURCE_TYPES[t][1]
            cx=(c['X']+0.5)*self.scale
            cy=(self.ny-c['Y']-0.5)*self.scale
            r=4 if self.scale>=2 else 3
            self.canvas.create_oval(cx-r,cy-r,cx+r,cy+r,fill=col,outline='#000000',width=1,
                                    tags=('source', 'ent:'+ent['Id']))
        self.mark_selection()
        self.draw_line_preview()
        self.draw_forest_preview()
        self.info.set(f'Carte {self.nx} × {self.ny} — {len(find_sources(self.parent.world))} sources/gisements affichés. Déplace la souris pour les coordonnées.')

    def draw_line_preview(self):
        self.canvas.delete('line_preview')
        if self.line_start and self.line_mode.get():
            x,y=self.line_start
            cx=(x+0.5)*self.scale; cy=(self.ny-y-0.5)*self.scale
            self.canvas.create_oval(cx-6,cy-6,cx+6,cy+6,outline='#ffea63',width=2,tags='line_preview')

    def toggle_line(self):
        if self.line_mode.get():self.forest_mode.set(False)
        self.line_start=None
        self.draw_line_preview()
        self.info.set('Mode ligne activé : clique le départ puis l’arrivée.' if self.line_mode.get() else 'Mode sélection simple activé.')

    def mark_selection(self):
        self.canvas.delete('selection')
        x=self.xvar.get();y=self.yvar.get()
        if 0<=x<self.nx and 0<=y<self.ny:
            px=x*self.scale;py=(self.ny-y-1)*self.scale
            self.canvas.create_rectangle(px-2,py-2,px+self.scale+2,py+self.scale+2,
                                         outline='#ffe477',width=2,tags='selection')

    def get_xy(self,event):
        px=self.canvas.canvasx(event.x);py=self.canvas.canvasy(event.y)
        return int(px//self.scale), self.ny-1-int(py//self.scale)

    def motion(self,event):
        x,y=self.get_xy(event)
        if 0<=x<self.nx and 0<=y<self.ny:
            self.info.set(f'X={x}, Y={y}, hauteur du terrain Z={self.heights[y*self.nx+x]}. Clique pour sélectionner.')

    def click(self,event):
        x,y=self.get_xy(event)
        if not (0<=x<self.nx and 0<=y<self.ny):return
        self.xvar.set(x);self.yvar.set(y);self.zvar.set(self.heights[y*self.nx+x]);self.selected_id=None
        if self.forest_mode.get():
            if self.forest_start is None:
                self.forest_start=(x,y)
                self.forest_rect=None
                self.info.set(self.t('forest_second'))
            else:
                self.forest_rect=(*self.forest_start,x,y)
                self.forest_start=None
                self.info.set(self.t('forest_selected'))
            self.draw_forest_preview()
            return
        if self.line_mode.get():
            if self.mode.get() != 'WaterSource':
                messagebox.showinfo('Mode ligne', 'Le tracé en ligne est réservé aux sources d’eau 1×1. Pour une source contaminée 3×3, utilise « Ajouter à ces coordonnées ».')
                return
            if self.line_start is None:
                self.line_start=(x,y)
                self.draw_line_preview()
                self.info.set(f'Départ ({x},{y}) enregistré. Clique sur la case d’arrivée.')
                return
            start=self.line_start
            self.line_start=None
            self.draw_line_preview()
            self.add_line(start,(x,y))
            return
        candidates=[s for s in find_sources(self.parent.world) if coords(s)['X']==x and coords(s)['Y']==y]
        if candidates:
            ent=candidates[-1]
            self.selected_id=ent['Id']
            self.zvar.set(coords(ent)['Z'])
            self.mode.set(ent['Template'])
            self.info.set(f'Sélection : {SOURCE_TYPES[ent["Template"]][0]} à X={x}, Y={y}, Z={self.zvar.get()}')
        else:
            self.info.set(f'Case X={x}, Y={y}, Z={self.zvar.get()} sélectionnée pour ajout.')
        self.mark_selection()

    def toggle_forest(self):
        if self.forest_mode.get():self.line_mode.set(False)
        self.forest_start=None
        self.forest_rect=None
        self.draw_line_preview()
        self.draw_forest_preview()

    def draw_forest_preview(self):
        self.canvas.delete('forest_preview')
        rect=self.forest_rect
        if self.forest_start and not rect:
            x,y=self.forest_start
            rect=(x,y,x,y)
        if rect:
            x0,y0,x1,y1=rect
            xa,xb=sorted((x0,x1));ya,yb=sorted((y0,y1))
            self.canvas.create_rectangle(xa*self.scale,(self.ny-yb-1)*self.scale,
                (xb+1)*self.scale,(self.ny-ya)*self.scale,
                outline='#a4f27d',width=2,tags='forest_preview')

    def plant_selection(self):
        from forest_editor import plant_forest
        if not self.forest_rect:
            messagebox.showinfo(self.t('forest_title'),self.t('forest_help'))
            return
        trees=[t for t,var in self.tree_flags.items() if var.get()]
        if not trees:
            messagebox.showinfo(self.t('warning'),self.t('select_trees'))
            return
        import copy
        draft=copy.deepcopy(self.parent.world)
        try:
            added=plant_forest(draft,self.forest_rect,trees,self.forest_density.get())
            if not added:raise ValueError(self.t('forest_empty'))
            if not messagebox.askyesno(self.t('forest_title'),self.t('forest_confirm',count=added)):
                return
            self.parent.world=draft
            self.parent._refresh()
            self.render()
            self.info.set(self.t('forest_done',count=added))
        except Exception as err:messagebox.showerror(self.t('error'),str(err))

    def add_line(self, start, end):
        try:
            points=line_points(*start,*end)
            if len(points)>128:
                raise ValueError('Une ligne ne peut pas dépasser 128 sources en une opération.')
            conflicts=[]; valid=[]
            for x,y in points:
                conflict=source_conflicts(self.parent.world,'WaterSource',x,y)
                if conflict: conflicts.append((x,y,conflict))
                else: valid.append((x,y))
            if not valid:
                messagebox.showwarning('Aucune case libre','Toutes les cases de cette ligne sont occupées ou interdites.')
                return
            strength=float(self.strength.get().replace(',','.'))
            if not 0<strength<=100: raise ValueError('Débit attendu entre 0 et 100.')
            message=f'Ajouter {len(valid)} sources d’eau sur la ligne de ({start[0]},{start[1]}) à ({end[0]},{end[1]}) ?'
            if conflicts: message+=f'\n{len(conflicts)} cases déjà occupées seront ignorées.'
            message+='\nChaque case sera placée à la hauteur locale du terrain.'
            if not messagebox.askyesno(self.t('warning'),message):return
            for x,y in valid:
                z=self.heights[y*self.nx+x]
                add_source(self.parent.world,'WaterSource',x,y,z,strength)
            self.render()
            self.parent.status.set(self.t('saved_info'))
        except Exception as e:
            messagebox.showerror(self.t('error'),str(e))

    def add(self):
        try:
            x,y,z=self.xvar.get(),self.yvar.get(),self.zvar.get()
            template=self.mode.get()
            strength=float(self.strength.get().replace(',','.'))
            if strength<=0 or strength>100:raise ValueError('Débit attendu entre 0 et 100.')
            terrain=self.heights[y*self.nx+x] if 0<=x<self.nx and 0<=y<self.ny else -1
            if z!=terrain:
                if not messagebox.askyesno('Altitude inhabituelle',f'Le relief à X={x} Y={y} est Z={terrain}, mais tu proposes Z={z}.\n\nContinuer malgré le risque ?'):
                    return
            if not messagebox.askyesno(self.t('warning'),f'Ajouter {SOURCE_TYPES[template][0]}\nX={x}, Y={y}, Z={z} ?\n\nLes objets multi-cases ne sont pas entièrement détectés.'):
                return
            new=add_source(self.parent.world,template,x,y,z,strength)
            self.selected_id=new['Id']
            self.render()
            self.parent.status.set(self.t('saved_info'))
        except Exception as e:
            messagebox.showerror(self.t('error'),str(e))

    def delete(self):
        if not self.selected_id:
            messagebox.showinfo('Sélection', 'Clique d’abord sur une ressource existante dans la carte.')
            return
        if not messagebox.askyesno(self.t('remove_source'), 'Supprimer cette source de la nouvelle sauvegarde ?'):
            return
        if remove_source(self.parent.world,self.selected_id):
            self.selected_id=None
            self.render()
            self.parent.status.set(self.t('saved_info'))
