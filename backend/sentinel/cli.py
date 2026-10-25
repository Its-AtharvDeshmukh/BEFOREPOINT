import argparse
import json
from pathlib import Path
from .evaluation import evaluate,twin_test
from .replay import Replay
from .simulator import SCENARIOS


def main():
    parser=argparse.ArgumentParser(description='BEFOREPOINT reproducible local tools')
    parser.add_argument('command',choices=['evaluate','twins','replay'])
    parser.add_argument('--output',type=Path)
    parser.add_argument('--scenario',choices=list(SCENARIOS),default='twin_crisis')
    parser.add_argument('--seed',type=int,default=26)
    args=parser.parse_args()
    if args.command=='evaluate': result=evaluate()
    elif args.command=='twins':result=twin_test(args.seed)
    else:
        r=Replay(args.scenario,args.seed)
        for _ in range(r.episode.duration):r.step()
        result=r.state()
    value=json.dumps(result,indent=2,allow_nan=False)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(value+'\n')
        print(f'Saved {args.output}')
    else:print(value)

if __name__=='__main__':main()
