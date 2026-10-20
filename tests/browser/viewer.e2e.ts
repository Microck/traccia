import {readFileSync} from 'node:fs';
import {test} from '@e2e-dev/web';
import {expect} from 'e2e';
const fixture=JSON.parse(readFileSync('.fixture/manifest.json','utf8')) as {adminNode:{id:string;name:string};hiddenId:string;publicNames:string[]};

for(const width of [1280,390])test(`public viewer search and panels at ${width}px`,async({app,browser,screen})=>{
 await browser.setViewport({width,height:900});
 await browser.emulateMedia({reducedMotion:'reduce'});
 await app.open('/viewer-public/');
 await expect(screen.getByText('Loading skill map...',{exact:true})).not.toBeVisible();
 await screen.getByRole('button',{name:'Toggle search',exact:true}).click();
 await screen.getByLabel('Search skills',{exact:true}).fill('no-such-synthetic-skill');
 await expect(screen.getByText('No nodes match the current filters.',{exact:true})).toBeVisible();
 await screen.getByRole('button',{name:'Clear search',exact:true}).click();
 await expect(screen.getByText('No nodes match the current filters.',{exact:true})).not.toBeVisible();
 await screen.getByRole('button',{name:'Toggle filters',exact:true}).click();
 await expect(screen.getByLabel('Search skills',{exact:true})).not.toBeVisible();
 await screen.getByRole('button',{name:'Toggle filters',exact:true}).click();
 expect(await browser.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('published bundle physically excludes hidden and raw provenance data',async({app,browser})=>{
 await app.open('/viewer-public/');
 const graph=await browser.evaluate(async()=>{const r=await fetch('graph.json');if(!r.ok)throw Error('graph fetch failed');return r.json();});
 expect(JSON.stringify(graph).includes(fixture.hiddenId)).toBe(false);
 const keys:string[]=[];
 function visit(value:unknown){if(Array.isArray(value))value.forEach(visit);else if(value&&typeof value==='object')for(const [key,item] of Object.entries(value)){keys.push(key);visit(item);}}
 visit(graph);
 for(const forbidden of ['provenance','evidenceId','sourceId','excerpt','filename','uri'])expect(keys.includes(forbidden)).toBe(false);
 expect(graph.nodes.length).toBeGreaterThan(0);
});

test('admin nodes are operable from the keyboard',async({app,browser,screen})=>{
 await app.open('/viewer-admin/');
 await expect(screen.getByText('Loading skill map...',{exact:true})).not.toBeVisible();
 await screen.getByRole('button',{name:fixture.adminNode.name,exact:true}).press('Enter');
 await expect(browser.locator('#drawer')).toBeVisible();
 await expect(screen.getByRole('heading',{name:fixture.adminNode.name,exact:true})).toBeVisible();
 await screen.getByRole('button',{name:'Close drawer (Esc)',exact:true}).click();
 await expect(browser.locator('#drawer')).not.toBeVisible();
 expect(await browser.evaluate(()=>document.activeElement?.getAttribute('data-id')??null)).toBe(fixture.adminNode.id);
 await screen.getByRole('button',{name:fixture.adminNode.name,exact:true}).press(' ');
 await expect(browser.locator('#drawer')).toBeVisible();
 await screen.getByRole('button',{name:'Close drawer (Esc)',exact:true}).press('Escape');
 await expect(browser.locator('#drawer')).not.toBeVisible();
 expect(await browser.evaluate(()=>document.activeElement?.getAttribute('data-id')??null)).toBe(fixture.adminNode.id);
});

test('admin drawer stays open after immediate close and reopen',async({app,browser,screen})=>{
 await app.open('/viewer-admin/');
 await expect(screen.getByText('Loading skill map...',{exact:true})).not.toBeVisible();
 const node=browser.locator(`[data-id="${fixture.adminNode.id}"]`);
 await node.click();
 await screen.getByRole('button',{name:'Close drawer (Esc)',exact:true}).click();
 await node.click();
 // Observe after the documented 250ms closing transition has elapsed.
 await browser.evaluate(()=>new Promise<null>(resolve=>setTimeout(()=>resolve(null),350)));
 await expect(browser.locator('#drawer')).toBeVisible();
});

test('admin hide and feature decisions download as real curation JSON',async({app,browser,screen})=>{
 await app.open('/viewer-admin/');
 await expect(screen.getByText('Loading skill map...',{exact:true})).not.toBeVisible();
 await browser.locator(`[data-id="${fixture.adminNode.id}"]`).click();
 await browser.locator('#toggle-hidden').click();
 await browser.locator('#toggle-featured').click();
 const download=await browser.waitForDownload(()=>screen.getByRole('button',{name:'Save',exact:true}).click());
 const saved=JSON.parse(readFileSync(download.absolutePath,'utf8'));
 expect(saved.version).toBe(1);
 expect(saved.nodes[fixture.adminNode.id].hidden).toBe(true);
 expect(saved.nodes[fixture.adminNode.id].featured).toBe(true);
});
