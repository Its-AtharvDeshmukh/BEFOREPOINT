import hashlib
import json
import sqlite3
from threading import RLock


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()

class ReceiptStore:
    def __init__(self,path=':memory:'):
        self.lock=RLock()
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('CREATE TABLE IF NOT EXISTS receipts(run TEXT, minute INTEGER, body TEXT, PRIMARY KEY(run,minute))')
        self.db.execute('CREATE TABLE IF NOT EXISTS observations(run TEXT, id TEXT, body TEXT, PRIMARY KEY(run,id))')
        self.db.execute('CREATE TABLE IF NOT EXISTS source_reliability(source TEXT PRIMARY KEY, alpha REAL, beta REAL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS source_adjudications(run TEXT, target TEXT, source TEXT, correct INTEGER, learned_minute INTEGER, PRIMARY KEY(run,target))')
        self.db.execute('CREATE TABLE IF NOT EXISTS run_metadata(run TEXT PRIMARY KEY, body TEXT)')
        self.db.execute('CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT, model_version TEXT, body TEXT)')
        self.db.commit()

    def event(self,run,event):
        with self.lock:
            self.db.execute('INSERT OR IGNORE INTO observations VALUES(?,?,?)',(run,event.id,event.model_dump_json()))
            self.db.commit()

    def append(self,run,body):
        with self.lock:
            rows=self.list(run)
            data={**body,'previous_hash':rows[-1]['hash'] if rows else '0'*64}
            data['hash']=digest(data)
            self.db.execute('INSERT INTO receipts VALUES(?,?,?)',(run,body['minute'],canonical(data)))
            self.db.commit()
            return data

    def list(self,run):
        with self.lock:
            return [json.loads(r[0]) for r in self.db.execute('SELECT body FROM receipts WHERE run=? ORDER BY minute',(run,))]

    def runs(self):
        with self.lock:
            return [r[0] for r in self.db.execute('SELECT DISTINCT run FROM receipts')]

    def verify(self,run):
        previous='0'*64
        rows=self.list(run)
        for row in rows:
            body={k:v for k,v in row.items() if k!='hash'}
            if row['previous_hash']!=previous or digest(body)!=row['hash']: return False
            previous=row['hash']
        return bool(rows)

    def source_priors(self):
        with self.lock:
            return {row[0]:[row[1],row[2]] for row in self.db.execute('SELECT source,alpha,beta FROM source_reliability')}

    def learn_sources(self,run,events,minute):
        with self.lock:
            by_id={e.id:e for e in events}
            for e in sorted(events,key=lambda e:(e.arrival_time,e.id)):
                if e.kind!='verification' or e.arrival_time>minute:continue
                target=by_id.get(e.retracts)
                if target is None or target.kind in ('verification','retraction'):continue
                correct=bool(e.payload['correct'])
                cursor=self.db.execute('INSERT OR IGNORE INTO source_adjudications VALUES(?,?,?,?,?)',
                    (run,target.id,target.source_id,int(correct),e.arrival_time))
                if cursor.rowcount:
                    self.db.execute('INSERT OR IGNORE INTO source_reliability VALUES(?,?,?)',(target.source_id,8.,2.))
                    self.db.execute('UPDATE source_reliability SET alpha=alpha+?,beta=beta+? WHERE source=?',
                        (int(correct),int(not correct),target.source_id))
            self.db.commit()

    def save_run(self,run,metadata):
        with self.lock:
            self.db.execute('INSERT OR REPLACE INTO run_metadata VALUES(?,?)',(run,canonical(metadata)))
            self.db.commit()

    def save_evaluation(self,version,result):
        with self.lock:
            self.db.execute('INSERT INTO evaluations(model_version,body) VALUES(?,?)',(version,canonical(result)))
            self.db.commit()

    def diagnostics(self):
        with self.lock:
            counts={table:self.db.execute('SELECT count(*) FROM '+table).fetchone()[0]
                for table in ('receipts','observations','run_metadata','source_reliability','source_adjudications','evaluations')}
            return {'sqlite_integrity':self.db.execute('PRAGMA quick_check').fetchone()[0],'stored_records':counts}
