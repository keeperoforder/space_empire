import unittest
from campaign import CampaignManager
class R:
 def __init__(self): self.amount=1000
 def add(self,n): self.amount=max(0,self.amount+n)
 def can_afford(self,n): return self.amount>=n
 def spend(self,n):
  if not self.can_afford(n): return False
  self.amount-=n; return True
class E:
 def __init__(self): self.resources={k:R() for k in ["metal","energy","crystals","fuel","credits","science"]}
 def get(self,k): return self.resources[k]
 def add(self,k,n): self.get(k).add(n)
 def can_afford(self,c): return all(self.get(k).can_afford(v) for k,v in c.items())
 def spend(self,c):
  if not self.can_afford(c): return False
  for k,v in c.items(): self.get(k).spend(v)
  return True
class O: pass
class Tests(unittest.TestCase):
 def setUp(self):
  self.e=E(); self.b=O(); self.b.owned={"mining_array":[{}]}; self.m=O(); self.m.delivered_total=120
  self.f=O(); self.f.ships=[]; self.t=O(); self.t.technologies={}
  self.g=O(); self.g.systems={"sol":{"discovered":True},"vega":{"discovered":True}}
  self.c=O(); self.c.colonies=[]
  self.x=CampaignManager(self.e,self.b,self.m,self.f,self.t,self.g,self.c)
 def test_eight_chapters(self): self.assertEqual(len(self.x.chapters),8)
 def test_mission_real_progress(self):
  self.x.update(0); self.assertEqual(self.x.missions["power"]["status"],"completed")
 def test_event_choices_affect_resources(self):
  before=self.e.get("science").amount; self.x.trigger_event("signal")
  ok,_=self.x.choose_event("decode")
  self.assertTrue(ok); self.assertEqual(self.e.get("science").amount,before+70)
  self.assertIn("signal_decoded",self.x.flags)
 def test_insufficient_cost(self):
  self.x.trigger_event("signal"); self.e.get("crystals").amount=0
  ok,_=self.x.choose_event("decode"); self.assertFalse(ok); self.assertIsNotNone(self.x.active_event)
 def test_snapshot_restore(self):
  self.x.trigger_event("asteroid"); state=self.x.snapshot()
  y=CampaignManager(self.e,self.b,self.m,self.f,self.t,self.g,self.c); y.restore(state)
  self.assertEqual(y.active_event["id"],"asteroid")
 def test_six_events(self): self.assertEqual(len(self.x.event_definitions),6)
if __name__=="__main__": unittest.main()
