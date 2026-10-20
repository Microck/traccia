import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
const nodes=Array.from({length:1000},(_,id)=>({id:`skill-${id}`,value:id}));
nodes.push({id:'skill-1',value:-1}); // Preserve Array.find's first-match semantics.
const endpoints=Array.from({length:10000},(_,i)=>`skill-${(i*37)%1000}`);
function indexed(){const index=new Map();for(const node of nodes)if(!index.has(node.id))index.set(node.id,node);return endpoints.map(id=>index.get(id));}
function baseline(){return endpoints.map(id=>nodes.find(node=>node.id===id));}
const expected=baseline();const actual=indexed();
for(let i=0;i<expected.length;i++)assert.equal(actual[i],expected[i]);
for(let pass=0;pass<5;pass++){
 const before=performance.now();baseline();const middle=performance.now();indexed();const after=performance.now();
 console.log(JSON.stringify({pass,baselineMs:middle-before,indexedMs:after-middle}));
}
