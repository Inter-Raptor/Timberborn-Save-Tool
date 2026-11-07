import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from save_engine import set_science, satisfy_beavers, set_difficulty
from forest_editor import eligible_tree_templates
from i18n import good_name, tr

class EngineTests(unittest.TestCase):
    def sample(self):
        return {'Singletons':{
          'ScienceService':{'SciencePoints':5},
          'DroughtWeather':{'MinDroughtDuration':2,'MaxDroughtDuration':4}},
          'Entities':[{'Template':'BeaverAdult','Components':{'NeedManager':{
            'Needs':[{'Name':'Hunger','Points':0.2},{'Name':'Thirst','Points':0.4}]}}},
            {'Template':'Oak','Components':{}}]}
    def test_science(self):
        w=self.sample();set_science(w,23456)
        self.assertEqual(w['Singletons']['ScienceService']['SciencePoints'],23456)
        with self.assertRaises(ValueError):set_science(w,-1)
    def test_one_time_needs(self):
        w=self.sample();self.assertEqual(satisfy_beavers(w),2)
        self.assertEqual(w['Entities'][0]['Components']['NeedManager']['Needs'][0]['Points'],1)
    def test_difficulty(self):
        w=self.sample();set_difficulty(w,{'DroughtWeather':(4,9)})
        self.assertEqual(w['Singletons']['DroughtWeather']['MaxDroughtDuration'],9)
        with self.assertRaises(ValueError):set_difficulty(w,{'DroughtWeather':(10,2)})
    def test_forest_types(self):self.assertEqual(eligible_tree_templates(self.sample()),['Oak'])
    def test_translations(self):
        self.assertEqual(good_name('Plank','fr'),'Planches')
        self.assertEqual(good_name('Plank','de'),'Bretter')
        self.assertEqual(tr('forest_title','es'),'Crear bosque')

if __name__=='__main__':unittest.main()
