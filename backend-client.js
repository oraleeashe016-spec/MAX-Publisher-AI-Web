'use strict';
const apiBaseKey='maxPublisherApiBase';
const apiSecretKey='maxPublisherApiKey';
const apiBase=()=>localStorage.getItem(apiBaseKey)||'';
const apiSecret=()=>sessionStorage.getItem(apiSecretKey)||'';
const byId=id=>document.getElementById(id);
function apiToast(message){if(typeof toast==='function')toast(message);}
function addBackendSettings(){
 const section=document.getElementById('settings'); if(!section||document.getElementById('backendPanel'))return;
 const panel=document.createElement('div'); panel.className='panel'; panel.id='backendPanel';
 panel.innerHTML='<div class="panel-head"><h3>Backend API v0.5</h3><span id="backendBadge" class="pill warn">не настроен</span></div><label class="field" for="apiBaseInput">HTTPS-адрес backend</label><input id="apiBaseInput" type="url" placeholder="https://your-api.example.com"><label class="field" for="apiSecretInput">APP_API_KEY</label><input id="apiSecretInput" type="password" autocomplete="off" placeholder="Ключ приложения (только на эту сессию)"><div class="row"><button class="btn alt" id="saveBackendBtn">Сохранить</button><button class="btn" id="checkBackendBtn">Проверить API</button></div><p id="backendStatus" class="muted">Backend ещё нужно развернуть отдельно от GitHub Pages.</p><p class="muted">Не вводи сюда токен MAX или ключ облачной модели. Они задаются только в переменных окружения backend.</p>';
 section.insertBefore(panel,section.children[2]||null);
 byId('apiBaseInput').value=apiBase();
 byId('saveBackendBtn').onclick=()=>{const value=byId('apiBaseInput').value.trim().replace(/\/$/,'');if(value&&!value.startsWith('https://')){apiToast('Нужен HTTPS-адрес');return;}localStorage.setItem(apiBaseKey,value);const secret=byId('apiSecretInput').value.trim();if(secret)sessionStorage.setItem(apiSecretKey,secret);else sessionStorage.removeItem(apiSecretKey);apiToast('Настройки backend сохранены');};
 byId('checkBackendBtn').onclick=async()=>{byId('saveBackendBtn').click();const base=apiBase();if(!base){apiToast('Сначала укажи адрес backend');return;}try{const r=await fetch(base+'/api/config');if(!r.ok)throw new Error('HTTP '+r.status);const d=await r.json();byId('backendBadge').textContent='доступен';byId('backendBadge').className='pill good';const active=(d.sources||[]).filter(x=>x.configured).length;byId('backendStatus').textContent='API '+d.version+' доступен. Источники настроены: '+active+'/5. AI: '+(d.ai.ollama_configured?'Ollama':(d.ai.cloud_configured?(d.ai.cloud_provider||'Cloud')+' · '+(d.ai.cloud_model||'модель настроена'):'не настроен'))+'. MAX: '+(d.max.configured?'да':'нет')+'.';apiToast('Backend отвечает');}catch(e){byId('backendBadge').textContent='ошибка';byId('backendStatus').textContent='Не удалось подключиться: '+e.message;apiToast('Backend недоступен');}};
}
const localSearch=window.runSearch;
window.runSearch=async function(){
 const base=apiBase(); if(!base){return localSearch();}
 const query=byId('query').value.trim(); const store=byId('store').value; const source=store==='all'?'all':({'Яндекс Маркет':'yandex_market','Ozon':'ozon','DNS':'dns','М.Видео':'mvideo','Ситилинк':'citilink'}[store]);
 byId('results').innerHTML='<div class="empty">Запрашиваем подключённые источники…</div>';
 try{const r=await fetch(base+'/api/search',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:query,source:source,min_discount:Number(byId('discountMin').value),limit:50})});if(!r.ok)throw new Error('HTTP '+r.status);const data=await r.json();
 found=(data.items||[]).map((x,i)=>({id:100000+i,name:x.name,store:stores.indexOf(x.source_name),price:x.price,old:x.old_price,discount:x.discount,cat:x.category,url:x.url,is_demo:false,source_name:x.source_name}));
 if(currentCategory!=='Все')found=found.filter(p=>p.cat===currentCategory);
 byId('resultCount').textContent=found.length+' товаров';
 byId('results').innerHTML=found.map((p,i)=>'<article class="product"><div class="product-top"><div><h3>'+safe(p.name)+'</h3><div class="product-meta">'+safe(p.source_name)+' · '+safe(p.cat)+'</div></div><span class="pill good">API</span></div><div class="price-line"><span class="price">'+money(p.price)+'</span>'+(p.old?'<span class="old">'+money(p.old)+'</span>':'')+(p.discount?'<span class="discount">−'+p.discount+'%</span>':'')+'</div><div class="product-actions"><button class="btn alt" onclick="toEditor('+i+')">В редактор</button><button class="btn ghost" onclick="openApiProduct('+i+')">Источник ↗</button></div></article>').join('')||'<div class="empty">В подключённых источниках ничего не найдено. Проверь feeds в backend.</div>';
 if(data.errors&&data.errors.length)apiToast('Часть источников недоступна');updateStats();
 }catch(e){byId('results').innerHTML='<div class="notice">Ошибка backend: '+safe(e.message)+'. Проверь HTTPS-адрес и настройки сервера.</div>';found=[];byId('resultCount').textContent='ошибка';updateStats();}
};
window.openApiProduct=function(i){const p=found[i];if(p&&p.url)window.open(p.url,'_blank','noopener');else apiToast('Ссылка не предоставлена источником');};
window.toEditor=function(i){const p=found[i]||products.find(x=>x.id===i);if(!p)return;byId('postTitle').value='🔥 Выгодное предложение дня';byId('postName').value=p.name;byId('postPrice').value=p.price||'';byId('postOld').value=p.old||'';byId('postUrl').value=p.url||'';byId('postText').value='Товар: '+p.name+'\nЦена: '+money(p.price)+(p.old?' вместо '+money(p.old):'')+(p.discount?'\nСкидка по данным источника: '+p.discount+'%':'')+'\nПроверь актуальную цену и наличие у продавца.';updatePreview();go('editor');apiToast(p.is_demo?'Демо-товар перенесён':'Товар из API перенесён');};
window.rewriteWithAI=async function(){
 const base=apiBase(),secret=apiSecret();
 if(!base||!secret){apiToast('Сначала настрой HTTPS backend и APP_API_KEY в разделе Настройки');return;}
 const name=byId('postName').value.trim();
 if(!name){apiToast('Сначала выбери RSS-новость или укажи название товара');return;}
 const rss=typeof currentRssItem!=='undefined'&&currentRssItem&&currentRssItem.url===byId('postUrl').value.trim();
 const item=rss?currentRssItem:null;
 const tone=byId('aiTone')?.value||'neutral';
 const payload={
  product_name:name,
  current_price:byId('postPrice').value,
  previous_price:byId('postOld').value,
  product_url:byId('postUrl').value,
  facts:byId('postText').value,
  tone:tone,
  content_type:rss?'rss':'product',
  source_name:item?.source_name||'',
  published_at:item?.published||''
 };
 const button=byId('rewriteAiBtn');if(button){button.disabled=true;button.textContent='AI обрабатывает…';}
 try{
  const r=await fetch(base+'/api/ai/draft',{method:'POST',headers:{'Content-Type':'application/json','X-API-Key':secret},body:JSON.stringify(payload)});
  const d=await r.json();if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));
  if(!d.text)throw new Error('AI вернул пустой текст');
  byId('postText').value=d.text;
  updatePreview();
  apiToast('Текст подготовлен: '+d.provider+(d.model?' · '+d.model:''));
 }catch(e){apiToast('AI API: '+e.message);}
 finally{if(button){button.disabled=false;button.textContent='✦ Переписать с AI';}}
};
window.makeDraft=async function(){
 const base=apiBase(),secret=apiSecret();
 if(base&&secret)return window.rewriteWithAI();
 const name=byId('postName').value.trim();
 if(!name){apiToast('Сначала укажи товар');return;}
 apiToast('Это локальный шаблон, не AI. Для AI настрой backend и APP_API_KEY.');
 const price=Number(byId('postPrice').value),old=Number(byId('postOld').value);
 const discount=old>price&&price?Math.round((1-price/old)*100):0;
 byId('postText').value='Нашли интересное предложение!\n\n'+name+'\\nЦена: '+(price?money(price):'уточняйте цену')+(old>price&&price?' вместо '+money(old):'')+(discount?'\nРазница по указанным ценам: '+discount+'%':'')+'\n\nПеред покупкой проверьте актуальную цену, наличие и условия доставки.';
 updatePreview();
};
window.renderQueue=function(){if(!drafts.length){byId('queue').innerHTML='<div class="empty">Сохранённых публикаций пока нет.</div>';return;}byId('queue').innerHTML=drafts.map(p=>'<div class="source-row" style="align-items:flex-start"><div style="min-width:0"><b>'+safe(p.name)+'</b><div class="muted">'+safe(p.created)+' · '+(p.price?money(p.price):'цена не указана')+'</div><div class="muted">'+safe(p.title)+'</div></div><div style="display:flex;gap:5px;flex-wrap:wrap"><button class="btn ghost" onclick="editDraft('+p.id+')">Открыть</button><button class="btn alt" onclick="sendApiDraft('+p.id+')">Отправить</button><button class="btn danger" onclick="deleteDraft('+p.id+')">×</button></div></div>').join('');};
window.sendApiDraft=async function(id){const p=drafts.find(x=>x.id===id),base=apiBase(),secret=apiSecret();if(!p)return;if(!base||!secret){apiToast('Настрой backend и APP_API_KEY в разделе Настройки');go('settings');return;}if(!confirm('Отправить этот пост в канал MAX?'))return;const text=[p.title,p.name,p.text,p.url].filter(Boolean).join('\n\n');try{const r=await fetch(base+'/api/max/publish',{method:'POST',headers:{'Content-Type':'application/json','X-API-Key':secret},body:JSON.stringify({text:text,confirmed:true})});const d=await r.json();if(!r.ok)throw new Error(d.detail||('HTTP '+r.status));apiToast('MAX подтвердил отправку');}catch(e){apiToast('Не отправлено: '+e.message);}};
document.addEventListener('DOMContentLoaded',addBackendSettings);
addBackendSettings();

/* RSS mode: public, read-only editorial feeds; never presented as live price data. */
window.searchMode='products';
window.setSearchMode=function(mode){
  window.searchMode=mode==='rss'?'rss':'products';
  const rss=window.searchMode==='rss';
  byId('modeProducts')?.classList.toggle('active',!rss);
  byId('modeRss')?.classList.toggle('active',rss);
  byId('rssFilters')?.classList.toggle('hide',!rss);
  byId('productFilters')?.classList.toggle('hide',rss);
  byId('searchModeHint').textContent=rss
    ?'RSS: открытые новости и обзоры техники. Это не лента цен и скидок.'
    :'Поиск предложений в подключённых товарных каталогах.';
  byId('query').placeholder=rss?'Например, смартфоны, видеокарты, ноутбуки':'Например, смартфон или SSD';
  byId('results').innerHTML='<div class="empty">'+(rss?'Нажми «Найти», чтобы загрузить открытые RSS-ленты.':'Выполни поиск товаров.')+'</div>';
  byId('resultCount').textContent='0 записей';
};
const productSearchWithBackend=window.runSearch;
window.runSearch=async function(){
  if(window.searchMode!=='rss')return productSearchWithBackend();
  return window.runRssSearch();
};
window.runRssSearch=async function(){
  const base=apiBase();
  if(!base){byId('results').innerHTML='<div class="notice">Для чтения RSS нужен запущенный backend. Сначала разверни backend и укажи HTTPS-адрес в Настройках.</div>';return;}
  const q=byId('query').value.trim(),source=byId('rssSource').value;
  byId('results').innerHTML='<div class="empty">Загружаем RSS-ленты…</div>';
  try{
    const params=new URLSearchParams({query:q,source,limit:'60'});
    const response=await fetch(base+'/api/rss/items?'+params.toString());
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||('HTTP '+response.status));
    found=(data.items||[]).map((item,i)=>({...item,id:'rss-'+i,is_rss:true,price:null,old:null,discount:0,cat:item.category}));
    byId('resultCount').textContent=found.length+' публикаций';
    byId('results').innerHTML=found.map((item,i)=>'<article class="product"><div class="product-top"><div><h3>'+safe(item.title)+'</h3><div class="product-meta">'+safe(item.source_name)+' · '+safe(item.category)+'</div></div><span class="pill">RSS</span></div><p class="muted">'+safe(item.summary||'В источнике нет краткого описания.')+'</p><div class="product-meta">'+safe(item.published||'Дата не указана')+'</div><div class="product-actions" style="margin-top:10px"><button class="btn alt" onclick="rssToEditor('+i+')">Подготовить пост</button><button class="btn ghost" onclick="openRssItem('+i+')">Открыть источник ↗</button></div></article>').join('')||'<div class="empty">В выбранной RSS-ленте ничего не найдено.</div>';
    if(data.errors?.length)apiToast('Некоторые RSS-ленты временно недоступны');
    updateStats();
  }catch(e){byId('results').innerHTML='<div class="notice">Не удалось загрузить RSS: '+safe(e.message)+'</div>';byId('resultCount').textContent='ошибка';}
};
window.openRssItem=function(i){const item=found[i];if(item?.url)window.open(item.url,'_blank','noopener');};
window.rssToEditor=function(i){
  const item=found[i];if(!item)return;
  byId('postTitle').value='📰 '+item.title;
  byId('postName').value=item.title;
  byId('postPrice').value='';
  byId('postOld').value='';
  byId('postUrl').value=item.url||'';
  byId('postText').value=[item.summary||'Краткое описание отсутствует.', 'Источник: '+item.source_name, item.published?'Дата: '+item.published:'', 'Материал источника: '+item.url, 'Перед публикацией проверь факты и соблюдай правила цитирования и использования материалов источника.'].filter(Boolean).join('\n\n')
  updatePreview();go('editor');apiToast('Материал RSS перенесён в редактор');
};
async function renderRssFeedList(){
 const target=byId('rssFeedList');if(!target)return;
 const feeds=[
 ['iXBT — Новости','https://www.ixbt.com/export/news/rss.xml'],
 ['iXBT — Статьи и обзоры','https://www.ixbt.com/export/articles/rss.xml'],
 ['3DNews — Hardware','https://3dnews.ru/news/rss/'],
 ['3DNews — Software','https://3dnews.ru/software-news/rss/'],
 ['3DNews — Смартфоны','https://3dnews.ru/phone/rss/'],
 ['Overclockers — Новости','https://overclockers.ru/rss/news.rss'],
 ['Overclockers — Обзоры','https://overclockers.ru/rss/lab.rss']
 ];
 target.innerHTML=feeds.map(f=>'<div class="source-row"><span>'+safe(f[0])+'</span><a href="'+f[1]+'" target="_blank" rel="noopener">Открыть RSS ↗</a></div>').join('');
}
document.addEventListener('DOMContentLoaded',renderRssFeedList);
renderRssFeedList();
