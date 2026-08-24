const decisions = [
  {type:'candidate', initials:'林', name:'林晓', meta:'数据架构师 · 匹配度 92%', note:'3 项核心技能命中，薪资期望略高于预算', color:'#f2d48a', action:'查看证据'},
  {type:'role', initials:'数', name:'数据架构师', meta:'JD 草稿 · 技术平台部', note:'建议将“数据中台”替换为“数据架构与治理”', color:'#b8d6ba', action:'审阅建议'},
  {type:'candidate', initials:'周', name:'周宁', meta:'产品经理 · 匹配度 88%', note:'有 B 端复杂产品经验，需确认团队管理范围', color:'#efb4a7', action:'查看证据'},
  {type:'interview', initials:'王', name:'王璐', meta:'Java 专家 · 面试待确认', note:'AI 找到 3 个双方都空闲的时段', color:'#cadb7b', action:'确认时段'},
  {type:'candidate', initials:'陈', name:'陈思远', meta:'算法工程师 · 匹配度 84%', note:'学校信息待核验，项目经历与 JD 高度相关', color:'#c4d6ce', action:'查看证据'},
  {type:'role', initials:'云', name:'云原生开发', meta:'渠道诊断 · 技术平台部', note:'薪资中位数低于市场估值约 15%', color:'#efc38a', action:'查看诊断'}
];
const candidates = [
  {initials:'林',name:'林晓',meta:'8 年经验 · 上海交通大学',score:92,tags:['数据架构','治理'] ,color:'#f2d48a'},
  {initials:'周',name:'周宁',meta:'6 年经验 · 浙江大学',score:88,tags:['B 端产品','平台'] ,color:'#efb4a7'},
  {initials:'陈',name:'陈思远',meta:'5 年经验 · 华中科技大学',score:84,tags:['算法','Python'] ,color:'#c4d6ce'},
  {initials:'赵',name:'赵一鸣',meta:'7 年经验 · 同济大学',score:81,tags:['数据中台','SQL'] ,color:'#cadb7b'}
];
const roles = [
  {title:'数据架构师',team:'技术平台部',status:'需关注',warn:true,meta:['18 份简历','¥35–50K'],progress:68},
  {title:'产品经理',team:'企业服务部',status:'招聘中',meta:['32 份简历','¥25–40K'],progress:54},
  {title:'Java 专家',team:'研发中心',status:'招聘中',meta:['11 份简历','¥30–45K'],progress:42},
  {title:'云原生开发',team:'技术平台部',status:'需诊断',warn:true,meta:['9 份简历','¥28–42K'],progress:30},
  {title:'算法工程师',team:'智能应用部',status:'招聘中',meta:['24 份简历','¥30–55K'],progress:76},
  {title:'交付总监',team:'项目管理部',status:'招聘中',meta:['6 份简历','¥40–60K'],progress:21}
];
const labels={overview:'总览',roles:'岗位',candidates:'候选人',interviews:'面试',analytics:'数据看板'};
const list=document.querySelector('#decision-list');
function renderDecisions(filter='all'){
  list.innerHTML=decisions.filter(d=>filter==='all'||d.type===filter).map((d,i)=>`<div class="decision-row"><div class="decision-avatar" style="background:${d.color}">${d.initials}</div><div class="decision-main"><strong>${d.name}</strong><p>${d.note}</p></div><div class="decision-side"><span class="decision-type">${d.meta}</span><button class="decision-action" data-action="${d.action}" data-index="${i}">${d.action}</button></div></div>`).join('');
  list.querySelectorAll('.decision-action').forEach(btn=>btn.addEventListener('click',()=>{
    const d=decisions[Number(btn.dataset.index)];
    if(d.type==='candidate') openDrawer(d); else showToast(`${btn.dataset.action}：${d.name}`);
  }));
}
function renderRoles(){document.querySelector('#role-grid').innerHTML=roles.map(r=>`<article class="role-card"><div class="role-card-top"><div><h3>${r.title}</h3><p>${r.team}</p></div><span class="role-status ${r.warn?'warn':''}">${r.status}</span></div><div class="role-meta"><span>${r.meta[0]}</span><span>${r.meta[1]}</span></div><div class="role-progress"><i style="width:${r.progress}%"></i></div></article>`).join('')}
function renderCandidates(){document.querySelector('#candidate-list').innerHTML=candidates.map(c=>`<div class="candidate-row"><div class="decision-avatar" style="background:${c.color}">${c.initials}</div><div><h4>${c.name}</h4><p>${c.meta}</p></div><div class="candidate-tags">${c.tags.map(t=>`<span>${t}</span>`).join('')}</div><strong class="candidate-score">${c.score}</strong></div>`).join('')}
function showView(view){document.querySelectorAll('.page-view').forEach(el=>el.classList.toggle('active',el.id===`${view}-view`));document.querySelectorAll('.nav-item').forEach(el=>el.classList.toggle('active',el.dataset.view===view));document.querySelector('#view-label').textContent=labels[view];window.scrollTo({top:0,behavior:'smooth'})}
function showToast(message){const toast=document.querySelector('#toast');toast.querySelector('p').textContent=message;toast.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>toast.classList.remove('show'),2600)}
function openDrawer(d){const drawer=document.querySelector('#candidate-drawer');document.querySelector('#drawer-content').innerHTML=`<div class="drawer-kicker">候选人证据卡 · AI 建议</div><h2 class="drawer-title">${d.name}</h2><p class="drawer-sub">${d.meta}</p><div class="drawer-score"><div><small>综合匹配度</small><strong>92</strong><small>/ 100</small></div><span>高匹配</span></div><div class="drawer-section"><h4>亮点证据</h4><div class="evidence-list"><span>✓ 8 年数据平台架构经验</span><span>✓ 有数据治理体系从 0 到 1 经历</span><span>✓ 带领过 12 人技术团队</span></div></div><div class="drawer-section"><h4>需要确认</h4><p>薪资期望为 ¥52K，高于岗位预算上限约 4%。建议在面试前确认总包结构与到岗时间。</p></div><div class="drawer-section"><h4>下一步建议</h4><button class="primary-btn" onclick="showToast('已生成面试邀约草稿')">生成面试邀约</button></div>`;document.querySelector('#drawer-backdrop').classList.add('open');drawer.classList.add('open')}
function closeDrawer(){document.querySelector('#drawer-backdrop').classList.remove('open');document.querySelector('#candidate-drawer').classList.remove('open')}
document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>showView(btn.dataset.view)));
document.querySelectorAll('[data-view-target]').forEach(btn=>btn.addEventListener('click',()=>showView(btn.dataset.viewTarget)));
document.querySelectorAll('.tab').forEach(tab=>tab.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));tab.classList.add('active');renderDecisions(tab.dataset.filter)}));
document.querySelector('#drawer-close').addEventListener('click',closeDrawer);document.querySelector('#drawer-backdrop').addEventListener('click',closeDrawer);
document.querySelector('#refresh-btn').addEventListener('click',()=>showToast('数据已刷新 · AI 建议保持最新'));
document.querySelector('#diagnose-btn').addEventListener('click',()=>showToast('正在打开岗位可招性诊断'));
document.querySelector('#schedule-btn').addEventListener('click',()=>showToast('已生成 3 个可用面试时段'));
document.querySelector('#send-invites-btn').addEventListener('click',()=>showToast('已准备 4 封面试邀约草稿'));
document.querySelector('#export-btn').addEventListener('click',()=>showToast('报告导出已准备（演示）'));
document.querySelectorAll('#create-role-btn,#create-role-btn-2').forEach(btn=>btn.addEventListener('click',()=>showToast('新建岗位流程已打开（演示）')));
document.querySelector('#search-input').addEventListener('input',e=>{if(e.target.value.trim())showToast(`正在搜索“${e.target.value.trim()}”`)});
renderDecisions();renderRoles();renderCandidates();
