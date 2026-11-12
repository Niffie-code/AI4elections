import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateFile,MAX_SIZE} from './validation.js';
test('accepts JPG and PNG at the size boundary',()=>{for(const type of ['image/jpeg','image/png']) assert.equal(validateFile({type,size:MAX_SIZE}),'');});
test('rejects missing, oversized, empty and unsupported uploads',()=>{for(const f of [null,{type:'image/png',size:MAX_SIZE+1},{type:'image/png',size:0},{type:'image/svg+xml',size:200}]) assert.ok(validateFile(f));});
