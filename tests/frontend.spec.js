import {test,expect} from '@playwright/test';
test('three demo outcomes and source modal',async({page})=>{
 const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto('/');
 for(const [choice,title] of [['A date has changed','Differences found'],['The visible text matches','Visible content matches'],['No reliable source found','Unable to verify']]){
  await page.getByRole('button',{name:'Try an example',exact:true}).click();
  await page.getByRole('button',{name:choice}).click();
  await expect(page.getByRole('heading',{name:title,exact:true})).toBeVisible();
  if(title==='Differences found'){
   await page.getByRole('button',{name:'View source',exact:true}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).not.toBeVisible();
   if(test.info().project.name==='mobile'){await page.getByRole('button',{name:'Reference source',exact:true}).click();await expect(page.locator('.comparison-source')).toBeVisible();}
  }
  await page.getByRole('button',{name:'Check another notice',exact:true}).click();
 }
 expect(errors).toEqual([]);
});
test('navigation, source search and no horizontal overflow',async({page})=>{
 await page.goto('/');if(test.info().project.name==='mobile')await page.getByRole('button',{name:'Toggle navigation'}).click();
 await page.getByRole('button',{name:'Sources',exact:true}).click();await page.getByRole('textbox',{name:'Search sources'}).fill('not-in-the-collection');await expect(page.getByRole('heading',{name:'No sources found'})).toBeVisible();await page.getByRole('button',{name:'Clear search',exact:true}).last().click();await expect(page.getByRole('heading',{name:'Community Civic Workshop'})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBeTruthy();
 if(test.info().project.name==='mobile')await page.getByRole('button',{name:'Toggle navigation'}).click();await page.getByRole('button',{name:'How it works',exact:true}).click();await expect(page.getByRole('heading',{name:'Clarity includes knowing the limits.'})).toBeVisible();
});
test('real upload remains unverified without backend; invalid files are rejected',async({page})=>{
 await page.goto('/');await page.locator('input[type=file]').setInputFiles({name:'bad.txt',mimeType:'text/plain',buffer:Buffer.from('not an image')});await expect(page.getByRole('alert')).toContainText('JPG or PNG');
 const data=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=100;c.height=100;const x=c.getContext('2d');x.fillStyle='#eee';x.fillRect(0,0,100,100);return c.toDataURL().split(',')[1]});
 await page.locator('input[type=file]').setInputFiles({name:'test-notice.png',mimeType:'image/png',buffer:Buffer.from(data,'base64')});await expect(page.getByAltText('Your selected notice')).toBeVisible();await page.getByRole('button',{name:'Check notice',exact:true}).click();await expect(page.getByRole('heading',{name:'Unable to verify',exact:true})).toBeVisible();await expect(page.getByText(/Your image has stayed in your browser/)).toBeVisible();
});
