"""Read-only React structure preflight using the sandbox's installed Vite toolchain."""

HOOK_PREFLIGHT = r'''
const fs=require('node:fs'), path=require('node:path');
const {transformSync}=require('esbuild');
const {parseAst}=require('rollup/parseAst');
const failures=[];
const layoutWarnings=[];
function inspect(file){
 const code=transformSync(fs.readFileSync(file,'utf8'),{sourcefile:file.split(path.sep).join('/') ,loader:file.endsWith('.tsx')?'tsx':file.endsWith('.ts')?'ts':'jsx',format:'esm',jsx:'automatic'}).code;
 const ast=parseAst(code), aliases=new Set(), defaults=new Set(), jsxFactories=new Set();
 for(const statement of ast.body){
  if(statement.type==='ImportDeclaration')for(const item of statement.specifiers||[]){
   if(/^react\/jsx(?:-dev)?-runtime$/.test(statement.source.value)&&['jsx','jsxs','jsxDEV'].includes(item.imported?.name))jsxFactories.add(item.local.name);
   if(/^use[A-Z]/.test(item.imported?.name||''))aliases.add(item.local.name);
  }
  if(statement.type==='ExportNamedDeclaration')for(const item of statement.specifiers||[]){
   if(item.exported?.name==='default')defaults.add(item.local.name);
  }
 }
 function nestedTypes(fn){
  const names=new Set();
  for(const statement of fn.body?.type==='BlockStatement'?fn.body.body:[]){
   if(['FunctionDeclaration','ClassDeclaration'].includes(statement.type)&&/^[A-Z]/.test(statement.id?.name||''))names.add(statement.id.name);
   if(statement.type==='VariableDeclaration')for(const declaration of statement.declarations){
    const init=declaration.init, wrapper=init?.type==='CallExpression'&&(init.callee.name||init.callee.property?.name);
    if(/^[A-Z]/.test(declaration.id?.name||'')&&(['ArrowFunctionExpression','FunctionExpression','ClassExpression'].includes(init?.type)||['memo','forwardRef'].includes(wrapper)))names.add(declaration.id.name);
   }
  }
  return names;
 }
 function localBindings(fn){
  const names=new Set();
  function pattern(node){
   if(!node)return;
   if(node.type==='Identifier')names.add(node.name);
   else if(node.type==='AssignmentPattern')pattern(node.left);
   else if(node.type==='RestElement')pattern(node.argument);
   else if(node.type==='ArrayPattern')node.elements.forEach(pattern);
   else if(node.type==='ObjectPattern')node.properties.forEach(p=>pattern(p.value||p.argument));
  }
  fn.params.forEach(pattern);
  for(const statement of fn.body?.type==='BlockStatement'?fn.body.body:[]){
   if(['FunctionDeclaration','ClassDeclaration'].includes(statement.type))pattern(statement.id);
   if(statement.type==='VariableDeclaration')statement.declarations.forEach(d=>pattern(d.id));
  }
  return names;
 }
 function walk(node,parent,scope){
  if(!node||typeof node!=='object')return;
  if(['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(node.type)){
   const name=node.id?.name||(parent?.type==='VariableDeclarator'?parent.id?.name:'')||'';
   const wrapper=parent?.type==='CallExpression'&&(parent.callee.name||parent.callee.property?.name);
   const allowed=!node.async&&(
    /^[A-Z]/.test(name)||/^use[A-Z]/.test(name)||defaults.has(name)||
    parent?.type==='ExportDefaultDeclaration'||['memo','forwardRef'].includes(wrapper)||
    (parent?.type==='Property'&&parent.key?.name==='component'));
   scope={name:name||'<anonymous callback>',allowed,parent:scope,
    bindings:localBindings(node),
    nestedTypes:allowed&&!/^use[A-Z]/.test(name)?nestedTypes(node):new Set()};
  }
  if(node.type==='CallExpression'){
   const callee=node.callee, name=callee?.type==='Identifier'?callee.name:callee?.type==='MemberExpression'?callee.property?.name:'';
   if(jsxFactories.has(name)&&node.arguments[0]?.type==='Identifier'){
    const rendered=node.arguments[0].name;
    for(let owner=scope;owner;owner=owner.parent)if(owner.bindings.has(rendered)){
     if(owner.nestedTypes.has(rendered))failures.push(file+': React component '+rendered+' is defined inside '+owner.name+' and rendered as a component. Move its definition to module scope and pass state/actions through props. Recreating a component type during rendering remounts its subtree and loses input focus/state.');
     break; // A parameter/local binding shadows the enclosing component name.
    }
   }
   if(jsxFactories.has(name)&&typeof node.arguments[0]?.value==='string'&&!node.arguments[0].value.includes('-')){
    const corrections={'class':'className','for':'htmlFor','stop-color':'stopColor','stop-opacity':'stopOpacity',
     'stroke-width':'strokeWidth','stroke-linecap':'strokeLinecap','stroke-linejoin':'strokeLinejoin',
     'stroke-dasharray':'strokeDasharray','stroke-dashoffset':'strokeDashoffset','stroke-opacity':'strokeOpacity',
     'fill-rule':'fillRule','fill-opacity':'fillOpacity','clip-rule':'clipRule','clip-path':'clipPath',
     'color-interpolation':'colorInterpolation','flood-color':'floodColor','flood-opacity':'floodOpacity',
     'font-size':'fontSize','font-family':'fontFamily','text-anchor':'textAnchor','tabindex':'tabIndex'};
    for(const property of node.arguments[1]?.properties||[]){
     const key=property.key?.name||property.key?.value;
     if(!property.computed&&corrections[key])failures.push(file+': invalid JSX property '+key+'. Use '+corrections[key]+' on React DOM elements.');
    }
   }
   if((/^use[A-Z]/.test(name||'')||aliases.has(name))&&(!scope||!scope.allowed)){
    failures.push(file+': '+name+' called in '+(scope?.name||'module scope')+'. Call hooks only at the top level of a React component or custom hook; never create a global hook result or call hooks in callbacks.');
   }
  }
  for(const [key,value] of Object.entries(node)){
   if(key==='parent')continue;
   if(Array.isArray(value)){
    for(const child of value)if(child?.type)walk(child,node,scope);
   }else if(value?.type){walk(value,node,scope);}
  }
 }
 // Browser-native dialogs block automation and provide no in-page state to
 // inspect. Check real AST calls, excluding strings, comments and local APIs.
 const moduleBindings=new Set();
 for(const statement of ast.body){
  const declaration=statement.declaration||statement;
  if(['FunctionDeclaration','ClassDeclaration'].includes(declaration.type)&&declaration.id)moduleBindings.add(declaration.id.name);
  if(declaration.type==='VariableDeclaration')for(const d of declaration.declarations)if(d.id.type==='Identifier')moduleBindings.add(d.id.name);
  if(statement.type==='ImportDeclaration')for(const s of statement.specifiers)moduleBindings.add(s.local.name);
 }
 function dialogs(node,bindings){
  if(!node||typeof node!=='object')return;
  if(['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(node.type))bindings=new Set([...bindings,...localBindings(node)]);
  if(node.type==='BlockStatement')bindings=new Set([...bindings,...localBindings({params:[],body:node})]);
  if(node.type==='CallExpression'){
   const c=node.callee, member=c?.type==='MemberExpression';
   const method=member?(c.computed?c.property?.value:c.property?.name):c?.name;
   const global=member?['window','globalThis','self'].includes(c.object?.name)&&!bindings.has(c.object.name):!bindings.has(method);
   if(global&&['alert','confirm','prompt'].includes(method))failures.push(file+': browser-native '+method+'() blocks the application workflow. Implement visible in-page feedback or an accessible confirmation dialog with explicit Confirm and Cancel actions; keep pending record identity in React state.');
  }
  for(const value of Object.values(node))if(Array.isArray(value)){for(const child of value)if(child?.type)dialogs(child,bindings);}else if(value?.type)dialogs(value,bindings);
 }
 dialogs(ast,moduleBindings);
 walk(ast,null,null);
}
function inspectCSS(file){
 const postcss=require('postcss');
 postcss.parse(fs.readFileSync(file,'utf8'),{from:file}).walkRules(rule=>{
  const declarations=(rule.nodes||[]).filter(n=>n.type==='decl');
  const reset=declarations.findLastIndex(d=>d.prop.toLowerCase()==='all'&&/^(unset|initial)$/i.test(d.value.trim()));
  if(reset<0)return;
  const full=declarations.some(d=>['width','inline-size'].includes(d.prop.toLowerCase())&&d.value.trim()==='100%');
  const expanded=declarations.some(d=>/^(padding(?:-.+)?|border(?:-(?:width|left|right))?)$/i.test(d.prop)&&!/^0(?:px|rem|em|%)?(?:\s+0(?:px|rem|em|%)?)*$/.test(d.value.trim())&&d.value!=='none');
  const restored=declarations.some((d,i)=>i>reset&&d.prop.toLowerCase()==='box-sizing'&&d.value.trim()==='border-box');
  if(full&&expanded&&!restored)layoutWarnings.push(file+': '+rule.selector+' resets box-sizing with all:'+declarations[reset].value+' and then adds padding/border to width:100%. Check the rendered cascade: restore box-sizing:border-box after the reset, or replace all:unset with explicit properties. This can make full-width cards/controls overflow on phones.');
 });
}
function scan(dir){
 for(const item of fs.readdirSync(dir,{withFileTypes:true})){
  const file=path.join(dir,item.name);
  if(item.isDirectory()){if(!['node_modules','dist','.git'].includes(item.name))scan(file);}
  else if(/.(jsx?|tsx?)$/.test(item.name)&&!item.name.endsWith('.d.ts')&&!item.name.endsWith('.gen.ts'))inspect(file);
  else if(item.name.endsWith('.css'))inspectCSS(file);
 }
}
try{if(fs.existsSync('src'))scan('src');}catch(error){console.error('React preflight could not parse source: '+error.message);process.exit(1);}
if(layoutWarnings.length)console.warn([...new Set(layoutWarnings)].join('\n'));
if(failures.length){console.error([...new Set(failures)].join('\n'));process.exit(1);}
console.log('React structure preflight passed (not exhaustive React validation).');
'''
