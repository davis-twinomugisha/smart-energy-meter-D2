"""Download the unchanged attributed UCI archive and verify its SHA-256."""
from pathlib import Path
import hashlib,urllib.request

ROOT=Path(__file__).resolve().parents[1]
URL='https://archive.ics.uci.edu/static/public/235/individual%2Bhousehold%2Belectric%2Bpower%2Bconsumption.zip'
SHA='9f84b46ade8a2d8e1286ec4b2b6c2987a45a755c59f263be3b3b3d10dfbda3ff'
if __name__=='__main__':
    path=ROOT/'data/raw/household_power_consumption.zip';path.parent.mkdir(parents=True,exist_ok=True)
    if not path.exists():
        temporary=path.with_suffix('.download')
        with urllib.request.urlopen(URL,timeout=120) as response,temporary.open('wb') as output:
            while chunk:=response.read(1024*1024):output.write(chunk)
        temporary.replace(path)
    actual=hashlib.sha256(path.read_bytes()).hexdigest()
    if actual!=SHA:raise SystemExit('Checksum mismatch: remove the archive and download again')
    print('Verified UCI archive:',path.name,actual)
