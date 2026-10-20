import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('.fixture/project/exports/',import.meta.url));
const python=fileURLToPath(new URL('../../.venv/bin/python',import.meta.url));
const child=spawn(python,['-m','http.server','4193','--bind','127.0.0.1','--directory',root],{stdio:'inherit'});
for(const signal of ['SIGINT','SIGTERM'])process.on(signal,()=>child.kill(signal));
child.once('error',error=>{console.error(error);process.exitCode=1;});
child.once('exit',code=>{process.exitCode=code??0;});
