"""Standalone, bounded source version storage executed inside the app sandbox."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import time
import uuid
import zipfile

MAX_BYTES = 25_000_000
MAX_FILES = 1000


def eligible(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name:
        return False
    if any(part in {'node_modules','dist','build','.git','__pycache__','recovered'} for part in path.parts):
        return False
    if any(part.startswith('.') for part in path.parts):
        return name in {'.genesys-design.json','.genesys-build-spec.json'}
    if re.search(r'(?:secret|credential|private[-_]?key|\.env)', name, re.I):
        return False
    return (path.parts[0] in {'src','public'} or len(path.parts)==1) and path.suffix.lower() in {
        '.js','.jsx','.ts','.tsx','.css','.scss','.html','.json','.svg','.png','.jpg','.jpeg','.webp','.woff','.woff2','.ico','.md'}


def files(root):
    result={}
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:]=[d for d in dirs if d not in {'node_modules','dist','build','recovered','__pycache__'} and not d.startswith('.') and not (Path(directory)/d).is_symlink()]
        for name in names:
            file=Path(directory)/name
            relative=file.relative_to(root).as_posix()
            if eligible(relative) and not file.is_symlink():
                result[relative]=file
    return result


def versions(store):
    records=[]
    for file in store.glob('*.json'):
        try:
            record=json.loads(file.read_text())
            if re.fullmatch(r'[0-9a-f]{32}',record['id']) and (store/(record['id']+'.zip')).is_file():
                records.append(record)
        except (ValueError,KeyError,OSError):
            continue
    return sorted(records,key=lambda r:r['createdAt'],reverse=True)


def capture(root,store,label):
    entries=files(root)
    if len(entries)>MAX_FILES or sum(p.stat().st_size for p in entries.values())>MAX_BYTES:
        raise ValueError('Source version exceeds the backup limit; build cancelled to preserve existing files.')
    version=uuid.uuid4().hex
    store.mkdir(parents=True,exist_ok=True)
    temp=store/(version+'.tmp')
    hashes={}
    try:
        total=0
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as archive:
            for name,file in sorted(entries.items()):
                if file.is_symlink() or not file.resolve().is_relative_to(root):
                    raise ValueError('Source changed during version capture')
                data=file.read_bytes();total+=len(data)
                if total>MAX_BYTES:raise ValueError('Source version exceeds backup limit')
                archive.writestr(name,data)
                hashes[name]=hashlib.sha256(data).hexdigest()
        temp.replace(store/(version+'.zip'))
        record={'id':version,'createdAt':time.time(),'label':str(label)[:100],
                'files':len(hashes),'bytes':total,'hashes':hashes,'verified':False}
        (store/(version+'.json')).write_text(json.dumps(record))
        records=versions(store)
        size=0
        for index,item in enumerate(records):
            size+=item['bytes']
            if index>=30 or (index>0 and size>200_000_000):
                (store/(item['id']+'.json')).unlink(missing_ok=True)
                (store/(item['id']+'.zip')).unlink(missing_ok=True)
        return {k:v for k,v in record.items() if k!='hashes'}
    finally:
        temp.unlink(missing_ok=True)


def restore(root,store,version,locks=()):
    if not re.fullmatch(r'[0-9a-f]{32}',version):raise ValueError('Invalid version')
    record=json.loads((store/(version+'.json')).read_text())
    content={};total=0
    with zipfile.ZipFile(store/(version+'.zip')) as archive:
        if len(archive.infolist())>MAX_FILES:raise ValueError('Invalid version archive')
        for info in archive.infolist():
            name=info.filename
            if not eligible(name) or name in content or info.file_size>MAX_BYTES:
                raise ValueError('Invalid version path')
            total+=info.file_size
            if total>MAX_BYTES:raise ValueError('Invalid version size')
            target=root/name
            if not target.resolve().is_relative_to(root) or target.is_symlink():
                raise ValueError('Unsafe restore destination')
            data=archive.read(info)
            if hashlib.sha256(data).hexdigest()!=record['hashes'].get(name):
                raise ValueError('Version integrity check failed')
            content[name]=data
    if set(content)!=set(record['hashes']):raise ValueError('Incomplete version archive')
    current=files(root)
    for name in set(current)|set(content):
        if any(name==p.rstrip('/') or (p.endswith('/') and name.startswith(p)) for p in locks):
            if name not in content or name not in current or current[name].read_bytes()!=content[name]:
                raise ValueError('Unfreeze affected files before restoring this source version')
    backup=capture(root,store,'Before source restore')
    for name,file in files(root).items():
        if name not in content:file.unlink()
    for name,data in content.items():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    return {'restored':version,'backup':backup['id'],'verified':False,
            'message':'Source restored. Build and browser verification are required before publishing.'}


def main():
    import sys
    root=Path(sys.argv[1]).resolve()
    store=root.parent/'.genesys-version-history'
    action=sys.argv[2];payload=json.loads(sys.argv[3])
    if action=='capture':result=capture(root,store,payload.get('label','Source version'))
    elif action=='list':result=[{k:v for k,v in r.items() if k!='hashes'} for r in versions(store)]
    elif action=='restore':result=restore(root,store,payload['id'],payload.get('locks',[]))
    else:raise ValueError('Invalid history action')
    print(json.dumps(result))


if __name__=='__main__':main()
