// Optional Node check of UI script and real HTTP API, with a minimal mocked DOM.
// This does not verify real-browser rendering or canvas appearance.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),cp=require('child_process'),path=require('path');
process.chdir(path.resolve(__dirname,'..'));
function element(){return {value:'',textContent:'',children:[],disabled:false,clientWidth:620,addEventListener(){},append(x){this.children.push(x)},replaceChildren(...x){this.children=x},getContext(){return new Proxy({},{get:()=>()=>{}})}}}
async function main(){
  const server=cp.spawn(process.env.CODEX_PRIMARY_RUNTIME_PYTHON||'python3',['-m','energy.server','--port','18765'],{stdio:'ignore'});
  try{
    let ready=false;
    for(let i=0;i<100;i++){
      try{const response=await fetch('http://127.0.0.1:18765/api/status');if(response.ok){ready=true;break}}catch(e){}
      await new Promise(r=>setTimeout(r,100));
    }
    assert(ready,'Local API did not start');
    const elements={};const document={getElementById(id){return elements[id]??=element()},createElement(){return element()}};
    const context={document,devicePixelRatio:1,fetch:(p,o)=>fetch('http://127.0.0.1:18765'+p,o),console};vm.createContext(context);
    const html=fs.readFileSync('web/index.html','utf8');
    vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1],context);
    for(let i=0;i<100&&!elements.example.children.length;i++)await new Promise(r=>setTimeout(r,20));
    assert.equal(elements.example.children.length,3);
    await vm.runInContext('run()',context);
    assert(Number(elements.next.textContent)>0);assert.equal(elements.comparison.children.length,4);assert.equal(elements.error.textContent,'');
    elements.balance.value='1000';await vm.runInContext('run()',context);assert.equal(elements.depletion.textContent,'>24');
    elements.balance.value='0';await vm.runInContext('run()',context);assert.equal(elements.depletion.textContent,'0.0');
    elements.history.value='-1';await vm.runInContext('run()',context);assert(elements.error.textContent.includes('24'));
    fs.writeFileSync('results/dashboard_script_checks.json',JSON.stringify({javascript_execution:'passed',example_loading:'passed',api_forecast:'passed',comparison_rows:'passed',horizon_censoring:'passed',zero_balance:'passed',invalid_history:'passed',environment:'Node VM with minimal mocked DOM/canvas and real local HTTP API',real_browser_rendering:'not performed; browser binary unavailable'},null,2));
    console.log('UI script/API checks passed. DOM/canvas mocked; real-browser rendering remains unverified.');
  }finally{server.kill()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
