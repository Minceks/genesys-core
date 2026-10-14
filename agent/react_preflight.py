"""Read-only React hook preflight using the sandbox's installed Vite toolchain."""

HOOK_PREFLIGHT = r'''
const fs=require('node:fs'), path=require('node:path');
const {transformSync}=require('esbuild');
const {parseAst}=require('rollup/parseAst');
const failures=[];
function inspect(file){
 const code=transformSync(fs.readFileSync(file,'utf8'),{loader:file.endsWith('.tsx')?'tsx':file.endsWith('.ts')?'ts':'jsx',format:'esm',jsx:'automatic'}).code;
 const ast=parseAst(code), aliases=new Set(), defaults=new Set();
 for(const statement of ast.body){
  if(statement.type==='ImportDeclaration')for(const item of statement.specifiers||[]){
   if(/^use[A-Z]/.test(item.imported?.name||''))aliases.add(item.local.name);
  }
  if(statement.type==='ExportNamedDeclaration')for(const item of statement.specifiers||[]){
   if(item.exported?.name==='default')defaults.add(item.local.name);
  }
 }
 function walk(node,parent,scope){
  if(!node||typeof node!=='object')return;
  if(['FunctionDeclaration','FunctionExpression','ArrowFunctionExpression'].includes(node.type)){
   const name=node.id?.name||(parent?.type==='VariableDeclarator'?parent.id?.name:'')||'';
   const wrapper=parent?.type==='CallExpression'&&(parent.callee.name||parent.callee.property?.name);
   scope={name:name||'<anonymous callback>',allowed:!node.async&&(
    /^[A-Z]/.test(name)||/^use[A-Z]/.test(name)||defaults.has(name)||
    parent?.type==='ExportDefaultDeclaration'||['memo','forwardRef'].includes(wrapper)||
    (parent?.type==='Property'&&parent.key?.name==='component'))};
  }
  if(node.type==='CallExpression'){
   const callee=node.callee, name=callee?.type==='Identifier'?callee.name:callee?.type==='MemberExpression'?callee.property?.name:'';
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
 walk(ast,null,null);
}
function scan(dir){
 for(const item of fs.readdirSync(dir,{withFileTypes:true})){
  const file=path.join(dir,item.name);
  if(item.isDirectory()){if(!['node_modules','dist','.git'].includes(item.name))scan(file);}
  else if(/.(jsx?|tsx?)$/.test(item.name)&&!item.name.endsWith('.d.ts')&&!item.name.endsWith('.gen.ts'))inspect(file);
 }
}
try{if(fs.existsSync('src'))scan('src');}catch(error){console.error('React preflight could not parse source: '+error.message);process.exit(1);}
if(failures.length){console.error(failures.join('\n'));process.exit(1);}
console.log('React hook placement preflight passed (not exhaustive rules-of-hooks validation).');
'''
