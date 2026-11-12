const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '');
export const backendConnected = Boolean(base);
export async function verifyImage(file, signal, onStage) {
 const body = new FormData(); body.append('file',file);
 const start = await fetch(`${base}/api/verifications`,{method:'POST',body,signal});
 if (!start.ok) throw new Error('The verification service could not accept this image. Please try again.');
 const job = await start.json();
 if (!job.id || !job.access_token) throw new Error('The service returned an incomplete job. Please contact the team.');
 for(let i=0;i<90;i++) {
  if(signal.aborted) throw new DOMException('Aborted','AbortError');
  const res=await fetch(`${base}/api/verifications/${encodeURIComponent(job.id)}`,{signal,headers:{Authorization:`Bearer ${job.access_token}`}});
  if(!res.ok) throw new Error('We could not retrieve your comparison. Please try again.');
  const data=await res.json();
  if(data.status==='failed') throw new Error('This image could not be processed. Try a clearer image.');
  onStage(data.stage || 'comparing');
  if(data.status==='completed') {
   if(!['match','differences','unverified'].includes(data.outcome)) throw new Error('The service returned an unsupported result.');
   return data;
  }
  await new Promise(resolve=>setTimeout(resolve,1500));
 }
 throw new Error('Verification is taking longer than expected. Please try again later.');
}
