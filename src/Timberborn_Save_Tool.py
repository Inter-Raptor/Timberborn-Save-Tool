"""Timberborn Save Tool — community save editor (v0.7, four languages)."""
import copy
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from save_engine import read_save, write_save, stock_summary, fill_stockpiles, add_characters, living_entities, difficulty_settings, set_difficulty, set_science, satisfy_beavers
from map_editor import MapEditor, SOURCE_TYPES
from forest_editor import eligible_tree_templates
from i18n import LANGUAGES, tr, good_name

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang=tk.StringVar(value='fr')
        self.members=self.world=self.original_world=self.source_path=None
        self.flags={}
        self.pop_count=tk.StringVar(value='10')
        self.age_days=tk.StringVar(value='15')
        self.science_points=tk.StringVar(value='0')
        self.diff_vars={}
        self.status=tk.StringVar()
        self.info=tk.StringVar()
        self.pop_info=tk.StringVar()
        self.title('Timberborn Save Tool')
        self.geometry('1220x900')
        self.minsize(960,660)
        self.configure(bg='#302a20')
        self._style()
        self._build()

    def t(self,k,**kw): return tr(k,self.lang.get(),**kw)
    def _style(self):
        s=ttk.Style(self);s.theme_use('clam')
        s.configure('Paper.TFrame',background='#f6f0e3')
        s.configure('Card.TFrame',background='#e7ddc5')
        s.configure('Note.TLabel',background='#f6f0e3',foreground='#625b4c',font=('Segoe UI',11))
        s.configure('Caption.TLabel',background='#e7ddc5',foreground='#60553f',font=('Segoe UI',10,'bold'))
        s.configure('Stock.TCheckbutton',background='#f6f0e3',foreground='#493e2f',font=('Segoe UI',10),padding=(7,6))
        s.configure('Forest.TNotebook',background='#ece3d0',borderwidth=0)
        s.configure('Forest.TNotebook.Tab',background='#d3c6a9',foreground='#4a412d',font=('Segoe UI',10,'bold'),padding=(16,12))
        s.map('Forest.TNotebook.Tab',background=[('selected','#f6f0e3')])
        for name,bg,fg,hover in [('Wood','#65543c','#f8ecd3','#827051'),('Gold','#d6a65c','#302718','#eac27e'),('Green','#52794d','#ffffff','#678b60'),('Outline','#e5dcc6','#4e4939','#f1e6cf')]:
            s.configure(f'{name}.TButton',background=bg,foreground=fg,font=('Segoe UI',10,'bold'),padding=(12,11))
            s.map(f'{name}.TButton',background=[('disabled','#aaa69c'),('active',hover)])
        s.configure('TEntry',padding=7);s.configure('TSpinbox',padding=7)

    def _heading(self,parent,title,sub):
        tk.Label(parent,text=title,bg='#f6f0e3',fg='#493824',font=('Georgia',19,'bold')).pack(anchor='w',padx=22,pady=(22,5))
        tk.Label(parent,text=sub,bg='#f6f0e3',fg='#77705f',font=('Segoe UI',10),wraplength=760).pack(anchor='w',padx=22,pady=(0,16))
        tk.Frame(parent,bg='#d5c7aa',height=1).pack(fill='x',padx=22)

    def set_lang(self,event=None):
        old_idx=self.tabs.index(self.tabs.select()) if hasattr(self,'tabs') else 0
        selected={g:v.get() for g,v in self.flags.items()}
        self._build()
        self.tabs.select(old_idx)
        self._refresh(selected)

    def _build(self):
        for child in self.winfo_children(): child.destroy()
        self.title('Timberborn Save Tool v0.7 — '+self.t('title'))
        header=tk.Frame(self,bg='#302a20',height=88);header.pack(fill='x');header.pack_propagate(False)
        tk.Label(header,text='◈',bg='#302a20',fg='#d5a95d',font=('Georgia',34)).pack(side='left',padx=(24,12))
        head=tk.Frame(header,bg='#302a20');head.pack(side='left',pady=12)
        tk.Label(head,text='TIMBERBORN SAVE TOOL',bg='#302a20',fg='#f5e7c8',font=('Georgia',20,'bold')).pack(anchor='w')
        tk.Label(head,text=self.t('title').upper()+'  ·  V0.7 BETA',bg='#302a20',fg='#c1ad88',font=('Segoe UI',10)).pack(anchor='w')
        picker=tk.Frame(header,bg='#302a20');picker.pack(side='right',padx=22)
        tk.Label(picker,text=self.t('language'),bg='#302a20',fg='#f5e7c8').pack(side='left',padx=9)
        combo=ttk.Combobox(picker,values=[f'{code.upper()} · {name}' for code,name in LANGUAGES.items()],state='readonly',width=17)
        combo.current(list(LANGUAGES).index(self.lang.get()))
        combo.pack(side='left')
        combo.bind('<<ComboboxSelected>>',lambda e:(self.lang.set(list(LANGUAGES)[combo.current()]),self.set_lang()))
        main=tk.Frame(self,bg='#ece3d0');main.pack(fill='both',expand=True)
        side=tk.Frame(main,bg='#40382b',width=220);side.pack(side='left',fill='y');side.pack_propagate(False)
        tk.Label(side,text=self.t('sidebar'),bg='#40382b',fg='#d8c49f',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=16,pady=(25,12))
        self.open_button=ttk.Button(side,text='📂 '+self.t('open'),style='Wood.TButton',command=self.open_save)
        self.open_button.pack(fill='x',padx=12,pady=5)
        self.save_button=ttk.Button(side,text='💾 '+self.t('save'),style='Gold.TButton',command=self.save)
        self.save_button.pack(fill='x',padx=12,pady=5)
        self.reset_button=ttk.Button(side,text='↶ '+self.t('reset'),style='Wood.TButton',command=self.reset)
        self.reset_button.pack(fill='x',padx=12,pady=5)
        tk.Frame(side,bg='#76694e',height=1).pack(fill='x',padx=16,pady=20)
        tk.Label(side,text=self.t('colony').upper(),bg='#40382b',fg='#d8c49f',font=('Segoe UI',10,'bold')).pack(anchor='w',padx=16)
        self.sidebar_info=tk.Label(side,text=self.source_path.stem if self.source_path else self.t('none'),bg='#40382b',fg='#f5e7c8',wraplength=190,justify='left')
        self.sidebar_info.pack(anchor='w',padx=16,pady=9)
        tk.Label(side,text=self.t('safe'),bg='#40382b',fg='#b6a88f',wraplength=188,justify='left').pack(side='bottom',padx=16,pady=22)
        mainarea=tk.Frame(main,bg='#ece3d0');mainarea.pack(side='left',fill='both',expand=True,padx=18,pady=13)
        tk.Label(mainarea,textvariable=self.info,bg='#ece3d0',fg='#5d594a',anchor='w').pack(fill='x',pady=(0,10))
        self.tabs=ttk.Notebook(mainarea,style='Forest.TNotebook');self.tabs.pack(fill='both',expand=True)
        pages=[]
        for key in ('home','resources','population','map'):
            page=ttk.Frame(self.tabs,style='Paper.TFrame');self.tabs.add(page,text='  '+self.t(key).upper()+'  ');pages.append(page)
        home,stock,pop,maptab=pages
        self._heading(home,self.t('dashboard'),self.t('dashboard_sub'))
        cards=ttk.Frame(home,style='Paper.TFrame');cards.pack(fill='x',padx=18,pady=16)
        self.dashboard_labels={}
        for i,(key,color) in enumerate([('beavers','#52794d'),('bots','#6b82a4'),('storages','#ad8958'),('sources','#4596b7')]):
            card=tk.Frame(cards,bg=color);card.grid(row=0,column=i,padx=4,sticky='nsew');cards.columnconfigure(i,weight=1)
            tk.Label(card,text=self.t(key).upper(),bg=color,fg='#f5ead6',font=('Segoe UI',10,'bold')).pack(pady=(14,4))
            lbl=tk.Label(card,text='—',bg=color,fg='white',font=('Georgia',24,'bold'));lbl.pack(pady=(0,16))
            self.dashboard_labels[key]=lbl
        shortcuts=ttk.Frame(home,style='Paper.TFrame');shortcuts.pack(fill='x',padx=23,pady=10)
        ttk.Label(shortcuts,text=self.t('quick').upper(),style='Note.TLabel').pack(anchor='w',pady=(4,9))
        ttk.Button(shortcuts,text=self.t('fill_all'),style='Green.TButton',command=self.fill_all).pack(anchor='w',pady=4)
        ttk.Button(shortcuts,text=self.t('heal_all'),style='Gold.TButton',command=self.heal_all).pack(anchor='w',pady=4)
        ttk.Button(shortcuts,text=self.t('open_map'),style='Outline.TButton',command=self.open_map).pack(anchor='w',pady=4)
        ttk.Label(home,text=self.t('safe')+' '+self.t('map_warning'),style='Note.TLabel',wraplength=730).pack(anchor='w',padx=23,pady=12)
        self._heading(stock,self.t('resources'),self.t('resources_sub'))
        actions=ttk.Frame(stock,style='Paper.TFrame');actions.pack(fill='x',padx=20,pady=12)
        ttk.Button(actions,text=self.t('fill_all'),style='Green.TButton',command=self.fill_all).pack(side='left',padx=(0,8))
        ttk.Button(actions,text=self.t('fill_selected'),style='Outline.TButton',command=self.fill_selected).pack(side='left')
        region=ttk.Frame(stock,style='Paper.TFrame');region.pack(fill='both',expand=True,padx=23,pady=8)
        self.canvas=tk.Canvas(region,bg='#f6f0e3',highlightthickness=0)
        scroll=ttk.Scrollbar(region,orient='vertical',command=self.canvas.yview)
        self.items_frame=ttk.Frame(self.canvas,style='Paper.TFrame')
        self.canvas.create_window((0,0),window=self.items_frame,anchor='nw')
        self.items_frame.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.configure(yscrollcommand=scroll.set)
        self.canvas.pack(side='left',fill='both',expand=True);scroll.pack(side='right',fill='y')
        self._heading(pop,self.t('population'),self.t('population_sub'))
        pcard=ttk.Frame(pop,style='Card.TFrame',padding=18);pcard.pack(fill='x',padx=20,pady=17)
        ttk.Label(pcard,text=self.t('count'),style='Caption.TLabel').grid(row=0,column=0,sticky='w',padx=(0,17))
        ttk.Label(pcard,text=self.t('age'),style='Caption.TLabel').grid(row=0,column=1,sticky='w')
        ttk.Entry(pcard,textvariable=self.pop_count,width=12).grid(row=1,column=0,pady=(8,17),sticky='w',padx=(0,17))
        ttk.Spinbox(pcard,from_=5,to=40,textvariable=self.age_days,width=12).grid(row=1,column=1,pady=(8,17),sticky='w')
        ttk.Button(pcard,text=self.t('add_beavers'),style='Green.TButton',command=lambda:self.add_population('beaver')).grid(row=2,column=0,sticky='w',padx=(0,10))
        ttk.Button(pcard,text=self.t('add_bots'),style='Outline.TButton',command=lambda:self.add_population('bot')).grid(row=2,column=1,sticky='w')
        ttk.Label(pop,textvariable=self.pop_info,style='Note.TLabel',wraplength=690).pack(anchor='w',padx=23,pady=8)
        ttk.Label(pop,text=self.t('bot_warning'),style='Note.TLabel',wraplength=690).pack(anchor='w',padx=23,pady=7)
        ttk.Button(pop,text=self.t('heal_all'),style='Green.TButton',command=self.heal_all).pack(anchor='w',padx=23,pady=13)
        needs_row=ttk.Frame(pop,style='Paper.TFrame');needs_row.pack(fill='x',padx=23,pady=8)
        ttk.Button(needs_row,text=self.t('feed_all'),style='Green.TButton',command=self.feed_all).pack(side='left',padx=(0,8))
        ttk.Button(needs_row,text=self.t('water_all'),style='Outline.TButton',command=self.water_all).pack(side='left')
        setup=ttk.LabelFrame(pop,text=self.t('settings_title'),padding=12)
        setup.pack(fill='x',padx=23,pady=12)
        science_row=ttk.Frame(setup);science_row.pack(fill='x',pady=5)
        ttk.Label(science_row,text=self.t('science'),width=25).pack(side='left')
        ttk.Entry(science_row,textvariable=self.science_points,width=18).pack(side='left',padx=7)
        ttk.Button(science_row,text=self.t('apply'),command=self.apply_science).pack(side='left')
        self.diff_vars={}
        for section,key in [('TemperateWeatherDurationService','temperate'),('DroughtWeather','drought'),('BadtideWeather','badtide')]:
            a=tk.StringVar();b=tk.StringVar();self.diff_vars[section]=(a,b)
            row=ttk.Frame(setup);row.pack(fill='x',pady=3)
            ttk.Label(row,text=self.t(key),width=25).pack(side='left')
            ttk.Entry(row,textvariable=a,width=8).pack(side='left',padx=7)
            ttk.Label(row,text='–').pack(side='left')
            ttk.Entry(row,textvariable=b,width=8).pack(side='left',padx=7)
        ttk.Button(setup,text=self.t('apply_difficulty'),command=self.apply_difficulty).pack(anchor='w',pady=6)
        self._heading(maptab,self.t('map'),self.t('map_sub'))
        ttk.Button(maptab,text=self.t('open_map'),style='Green.TButton',command=self.open_map).pack(anchor='w',padx=23,pady=20)
        ttk.Label(maptab,text=self.t('map_warning'),style='Note.TLabel',wraplength=680).pack(anchor='w',padx=23,pady=8)
        foot=tk.Frame(self,bg='#302a20',height=42);foot.pack(fill='x',side='bottom');foot.pack_propagate(False)
        tk.Label(foot,textvariable=self.status,bg='#302a20',fg='#e8d8b5',anchor='w',wraplength=1000).pack(fill='both',expand=True,padx=20)
        loaded=self.world is not None
        for btn in (self.save_button,self.reset_button):btn.configure(state='normal' if loaded else 'disabled')
        self._refresh()
        self.status.set(self.t('loaded') if loaded else self.t('ready'))

    def _refresh(self,prior=None):
        for w in self.items_frame.winfo_children(): w.destroy()
        prior=prior if prior is not None else {g:v.get() for g,v in self.flags.items()}
        self.flags={}
        if self.world is None:
            self.info.set(self.t('none'));self.pop_info.set(self.t('none'))
            return
        self.info.set(self.t('file_info',name=self.source_path.name,count=f'{len(self.world["Entities"]):,}'))
        self.sidebar_info.config(text=self.source_path.stem)
        summary=stock_summary(self.world)
        if not summary:ttk.Label(self.items_frame,text=self.t('no_stock'),style='Note.TLabel').pack(anchor='w')
        for good,(count,amount,capacity) in sorted(summary.items(),key=lambda pair:good_name(pair[0],self.lang.get()).casefold()):
            flag=tk.BooleanVar(value=prior.get(good,True));self.flags[good]=flag
            label=f'{good_name(good,self.lang.get())}   ·   {self.t("stock_count",count=count)}   ·   {amount:,} / {capacity:,}'
            ttk.Checkbutton(self.items_frame,text=label,variable=flag,style='Stock.TCheckbutton').pack(anchor='w',pady=2)
        cnt=lambda t:sum(e.get('Template')==t for e in self.world['Entities'])
        bots=len(list(living_entities(self.world,'bot')))
        totals={'beavers':cnt('BeaverAdult')+cnt('BeaverChild'),'bots':bots,'storages':sum(v[0] for v in summary.values()),'sources':sum(e.get('Template') in SOURCE_TYPES for e in self.world['Entities'])}
        for name,val in totals.items():self.dashboard_labels[name].config(text=str(val))
        self.pop_info.set(self.t('pop_info',adults=cnt('BeaverAdult'),children=cnt('BeaverChild'),bots=bots))
        self.science_points.set(str(self.world.get('Singletons',{}).get('ScienceService',{}).get('SciencePoints',0)))
        for sec,pair in difficulty_settings(self.world).items():
            if sec in self.diff_vars:
                self.diff_vars[sec][0].set(str(pair[0]));self.diff_vars[sec][1].set(str(pair[1]))

    def _require(self):return self.world is not None
    def open_save(self):
        p=filedialog.askopenfilename(title=self.t('choose_file'),filetypes=[('Timberborn','*.timber'),('All files','*.*')])
        if not p:return
        try:
            members,world=read_save(p)
            self.members,self.original_world,self.world,self.source_path=members,world,copy.deepcopy(world),Path(p)
            self._refresh()
            for btn in (self.save_button,self.reset_button):btn.config(state='normal')
            self.status.set(self.t('loaded'))
        except Exception as exc:messagebox.showerror(self.t('error'),str(exc))

    def fill_all(self):
        if not self._require():return
        changed=fill_stockpiles(self.world);self._refresh();self.status.set(self.t('fill_status',count=changed))
    def fill_selected(self):
        if not self._require():return
        goods={k for k,v in self.flags.items() if v.get()}
        if not goods:messagebox.showinfo(self.t('warning'),self.t('no_selection'));return
        changed=fill_stockpiles(self.world,goods);self._refresh();self.status.set(self.t('fill_status',count=changed))
    def heal_all(self):
        if not self._require():return
        n=changes=0
        for ent in self.world['Entities']:
            if ent.get('Template') not in ('BeaverAdult','BeaverChild'):continue
            needs=ent.get('Components',{}).get('NeedManager',{}).get('Needs',[])
            if not isinstance(needs,list):continue
            n+=1
            for need in needs:
                name=need.get('Name')
                v=-1.0 if name=='BadwaterContamination' else (1.0 if name in ('Hunger','Thirst','Sleep') else None)
                if v is not None and need.get('Points')!=v:need['Points']=v;changes+=1
        self.status.set(self.t('heal_status',count=n,changed=changes))
    def feed_all(self):
        if not self._require():return
        count=satisfy_beavers(self.world,hunger=True,thirst=False)
        self.status.set(self.t('needs_result',count=count))

    def water_all(self):
        if not self._require():return
        count=satisfy_beavers(self.world,hunger=False,thirst=True)
        self.status.set(self.t('needs_result',count=count))

    def apply_science(self):
        if not self._require():return
        try:
            value=set_science(self.world,self.science_points.get())
            self.status.set(self.t('science_result',count=value))
        except Exception as ex:messagebox.showerror(self.t('error'),str(ex))

    def apply_difficulty(self):
        if not self._require():return
        try:
            settings={k:(int(v[0].get()),int(v[1].get())) for k,v in self.diff_vars.items() if all(x.get() for x in v)}
            set_difficulty(self.world,settings)
            self.status.set(self.t('difficulty_result'))
        except Exception as ex:messagebox.showerror(self.t('error'),str(ex))

    def add_population(self,kind):
        if not self._require():return
        try:
            n=int(self.pop_count.get());age=int(self.age_days.get()) if kind=='beaver' else 15
            draft=copy.deepcopy(self.world)
            add_characters(draft,n,kind=kind,age_days=age)
            self.world=draft;self._refresh()
            self.status.set(self.t('add_status',count=n,kind=self.t('beavers' if kind=='beaver' else 'bots').lower()))
        except Exception as exc:messagebox.showerror(self.t('error'),str(exc))
    def open_map(self):
        if not self._require():return
        try:MapEditor(self)
        except Exception as exc:messagebox.showerror(self.t('error'),str(exc))
    def reset(self):
        if not self._require():return
        self.world=copy.deepcopy(self.original_world);self._refresh();self.status.set(self.t('reset_status'))
    def save(self):
        if not self._require():return
        suggested=self.source_path.with_name(self.source_path.stem+'_modifie.timber')
        filename=filedialog.asksaveasfilename(title=self.t('choose_save'),initialdir=str(suggested.parent),initialfile=suggested.name,defaultextension='.timber',filetypes=[('Timberborn','*.timber')])
        if not filename:return
        dest=Path(filename)
        if dest.resolve()==self.source_path.resolve():messagebox.showerror(self.t('warning'),self.t('protect'));return
        try:
            write_save(dest,self.members,self.world)
            self.status.set(self.t('saved',name=dest.name))
            messagebox.showinfo(self.t('saved',name=dest.name),self.t('saved_info'))
        except Exception as exc:messagebox.showerror(self.t('error'),str(exc))

if __name__=='__main__':App().mainloop()
