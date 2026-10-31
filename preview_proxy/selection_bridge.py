"""Inert until explicitly enabled by the Genesys editor parent."""
import zlib

LIMIT = 2_000_000
BRIDGE = b'''<script data-genesys-selection>
(()=>{if(window.parent===window)return;let enabled=false,origin='',nonce='';
const allowed=o=>o==='https://gene-sys.life'||o==='https://www.gene-sys.life';
window.addEventListener('message',e=>{if(e.source!==parent||!allowed(e.origin)||e.data?.type!=='genesys-selection-mode'||typeof e.data.nonce!=='string')return;
enabled=e.data.enabled===true;origin=e.origin;nonce=e.data.nonce;document.documentElement.style.cursor=enabled?'crosshair':'';});
document.addEventListener('click',e=>{if(!enabled||!origin)return;const node=e.target instanceof Element?e.target.closest('button,a,h1,h2,h3,p,img,label,input,section,article,div'):null;if(!node)return;
e.preventDefault();e.stopImmediatePropagation();
const element={tag:node.tagName.toLowerCase(),id:node.id.slice(0,100),role:(node.getAttribute('role')||'').slice(0,60),
label:(node.getAttribute('aria-label')||node.getAttribute('alt')||node.textContent||'').trim().slice(0,180),classes:[...node.classList].slice(0,8).join(' ').slice(0,160)};
parent.postMessage({type:'genesys-element-selected',nonce,element},origin);
enabled=false;document.documentElement.style.cursor='';},true);
})();</script>'''


def decoded(body, encoding):
    if encoding in {'','identity'}:return body
    if encoding!='gzip':return None
    reader=zlib.decompressobj(zlib.MAX_WBITS|16)
    try:html=reader.decompress(body,LIMIT+1)
    except zlib.error:return None
    return html if reader.eof else None


def inject(body, headers):
    if 'text/html' not in next((v for k,v in headers.items() if k.lower()=='content-type'),'').lower():
        return body
    encoding=next((v for k,v in headers.items() if k.lower()=='content-encoding'),'').strip().lower()
    html=decoded(body,encoding)
    # Selection is optional. A page it cannot read is served exactly as it arrived.
    if html is None or len(html)>LIMIT:return body
    for key in list(headers):
        if key.lower() in {'content-length','content-encoding','etag','last-modified'}:headers.pop(key)
    lower=html.lower();position=lower.rfind(b'</body>')
    return html[:position]+BRIDGE+html[position:] if position>=0 else html+BRIDGE
