"""Server-owned source references: models choose IDs instead of retyping code."""


def evidence_catalog(sources):
    catalog={}
    for path,code in sources.items():
        for start in range(0,len(code),800):
            excerpt=code[start:start+1000]
            if len(excerpt)<24:continue
            key=f'E{len(catalog)+1:03d}'
            catalog[key]={'path':path,'excerpt':excerpt}
    return catalog


def resolve_evidence(spec,catalog):
    for requirement in spec.get('requirements',[]):
        if requirement.get('scope')!='browser':continue
        reference=requirement.get('sourceEvidence')
        key=reference.get('referenceId') if isinstance(reference,dict) else None
        if not isinstance(key,str) or key not in catalog:
            raise ValueError(requirement['id']+': choose an existing sourceEvidence.referenceId from sourceEvidenceOptions')
        requirement['sourceEvidence']={**catalog[key],'referenceId':key}
    return spec
