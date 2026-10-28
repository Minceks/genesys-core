"""Bounded read-only comparisons of rendered canvas regions; never game-state hooks."""
FRAME_ACTIONS={'rememberFrame','frameChanged','frameStable'}


def validate_frame(step):
    if not isinstance(step.get('key'),str) or not step['key'].strip() or len(step['key'])>80:
        raise ValueError('Invalid verification plan: frame key must contain 1-80 characters')
    region=step.get('region')
    if region is not None:
        if not isinstance(region,dict) or set(region)!={'x','y','width','height'}:
            raise ValueError('Invalid verification plan: frame region needs x, y, width and height')
        if any(type(v) not in {int,float} for v in region.values()) or not (0<=region['x']<1 and 0<=region['y']<1 and .05<=region['width']<=1 and .05<=region['height']<=1 and region['x']+region['width']<=1 and region['y']+region['height']<=1):
            raise ValueError('Invalid verification plan: frame region must lie inside the canvas')
    threshold=step.get('threshold',.001)
    if type(threshold) not in {int,float} or not 0<=threshold<=(.001 if step.get('action')=='frameStable' else 1):
        raise ValueError('Invalid verification plan: frame threshold must be a pixel fraction 0-1')


def sample_canvas(locator,region=None):
    if locator.count()!=1 or not locator.is_visible():
        raise ValueError('Invalid verification plan: frame capture requires one visible canvas')
    try:
        return locator.evaluate("""(e,region)=>{
          if(e.tagName!=='CANVAS'||!e.width||!e.height)throw Error('Expected a nonempty canvas');
          const r=region||{x:0,y:0,width:1,height:1};
          const copy=document.createElement('canvas');copy.width=64;copy.height=64;
          const c=copy.getContext('2d',{willReadFrequently:true});
          c.drawImage(e,r.x*e.width,r.y*e.height,r.width*e.width,r.height*e.height,0,0,64,64);
          return Array.from(c.getImageData(0,0,64,64).data);
        }""",region)
    except Exception as error:
        raise ValueError('Invalid verification execution: canvas pixels are unavailable; source is preserved') from error


def perform_frame(locator,step,remembered):
    validate_frame(step)
    key=step['key'];region=step.get('region')
    pixels=sample_canvas(locator,region)
    if step['action']=='rememberFrame':
        if key not in remembered and len(remembered)>=16:
            raise ValueError('Invalid verification plan: at most sixteen captured frames')
        remembered[key]=(region,step.get('target'),pixels)
        return False
    if key not in remembered:
        raise ValueError('Invalid verification plan: capture frame before comparison')
    old_region,old_target,before=remembered[key]
    if old_region!=region or old_target!=step.get('target'):raise ValueError('Invalid verification plan: compare the same canvas target and region')
    changed=sum(max(abs(a-b) for a,b in zip(before[i:i+4],pixels[i:i+4]))>16 for i in range(0,len(pixels),4))/4096
    threshold=step.get('threshold',.001)
    if (step['action']=='frameChanged' and changed<=threshold) or (step['action']=='frameStable' and changed>threshold):
        raise AssertionError(f'Rendered canvas changed fraction {changed:.5f}; expected {step["action"]} with threshold {threshold}')
    return True
