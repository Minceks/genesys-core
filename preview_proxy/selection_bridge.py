"""Inert until explicitly enabled by the Genesys editor parent."""
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


def inject(body, headers):
    if 'text/html' not in next((v for k,v in headers.items() if k.lower()=='content-type'),'').lower():
        return body
    for key in list(headers):
        if key.lower() in {'content-length','content-encoding','etag'}:headers.pop(key)
    if len(body)>2_000_000:return body
    lower=body.lower();position=lower.rfind(b'</body>')
    return body[:position]+BRIDGE+body[position:] if position>=0 else body+BRIDGE
