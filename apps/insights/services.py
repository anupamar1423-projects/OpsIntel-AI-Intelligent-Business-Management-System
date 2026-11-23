from collections import defaultdict
from statistics import median
def detect_anomalies(org):
 from apps.operations.models import PipelineRun
 runs=list(PipelineRun.objects.filter(pipeline__organization=org).select_related("pipeline"));out=[]
 if len(runs)>=5:
  try:
   import numpy as np
   from sklearn.ensemble import IsolationForest
   X=np.array([[r.duration_minutes,int(r.status=="failed"),r.rows_processed] for r in runs]);m=IsolationForest(contamination=.12,random_state=42).fit(X); labels=m.predict(X);scores=-m.decision_function(X)
   return [(r,float(s),"Unusual duration/failure/volume") for r,l,s in zip(runs,labels,scores) if l<0 or r.status=="failed"]
  except (ImportError,ValueError):pass
 groups=defaultdict(list)
 for r in runs:groups[r.pipeline_id].append(r.duration_minutes)
 for r in runs:
  mid=median(groups[r.pipeline_id])
  if r.status=="failed" or (mid and r.duration_minutes>max(mid*2.5,mid+10)):out.append((r,.8,"Failed run" if r.status=="failed" else "Long duration vs median"))
 return out
def forecast(transactions):
 from collections import defaultdict
 m=defaultdict(float)
 for t in transactions:
  if t.kind=="expense":m[t.date.strftime("%Y-%m")]+=float(t.amount)
 return round(sum(list(m.values())[-6:])/len(m) if m else 0,2)
