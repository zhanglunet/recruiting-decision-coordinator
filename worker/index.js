const demoRoles = [
  { id: 'role-data-architect', title: '数据架构师', team: '技术平台部', status: '需关注', salary: '¥35–50K', candidates: 18, progress: 68 },
  { id: 'role-product-manager', title: '产品经理', team: '企业服务部', status: '招聘中', salary: '¥25–40K', candidates: 32, progress: 54 },
  { id: 'role-java-expert', title: 'Java 专家', team: '研发中心', status: '招聘中', salary: '¥30–45K', candidates: 11, progress: 42 },
  { id: 'role-cloud-native', title: '云原生开发', team: '技术平台部', status: '需诊断', salary: '¥28–42K', candidates: 9, progress: 30 },
  { id: 'role-algorithm', title: '算法工程师', team: '智能应用部', status: '招聘中', salary: '¥30–55K', candidates: 24, progress: 76 },
  { id: 'role-delivery-director', title: '交付总监', team: '项目管理部', status: '招聘中', salary: '¥40–60K', candidates: 6, progress: 21 }
];

const demoCandidates = [
  { id: 'candidate-linxiao', name: '林晓', role: '数据架构师', experience: '8 年经验', education: '上海交通大学', score: 92, skills: ['数据架构', '治理'], evidence: ['8 年数据平台架构经验', '有数据治理体系从 0 到 1 经历', '带领过 12 人技术团队'], concern: '薪资期望为 ¥52K，高于岗位预算上限约 4%。' },
  { id: 'candidate-zhouning', name: '周宁', role: '产品经理', experience: '6 年经验', education: '浙江大学', score: 88, skills: ['B 端产品', '平台'], evidence: ['负责过企业服务平台核心模块', '有复杂流程产品落地经历'], concern: '需确认团队管理范围。' },
  { id: 'candidate-chensiyuan', name: '陈思远', role: '算法工程师', experience: '5 年经验', education: '华中科技大学', score: 84, skills: ['算法', 'Python'], evidence: ['项目经历与岗位关键产出相关'], concern: '学校信息待核验。' }
];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { 'content-type': 'application/json; charset=UTF-8', 'cache-control': 'no-store' } });
}

async function readBody(request) {
  try { return await request.json(); } catch { return {}; }
}

async function enterpriseChat(env, messages) {
  const provider = String(env.MODEL_PROVIDER || 'glm').toLowerCase();
  const apiKey = provider === 'glm' ? env.GLM_API_KEY : env.ENTERPRISE_API_KEY;
  if (!apiKey) return null;
  const base = String(env.MODEL_BASE_URL || (provider === 'glm' ? 'https://open.bigmodel.cn/api/coding/paas/v4' : 'https://aigw.asiainfo.com/v1')).replace(/\/$/, '');
  const useStream = provider === 'glm';
  const response = await fetch(`${base}/chat/completions`, {
    method: 'POST',
    headers: { accept: 'application/json', authorization: `Bearer ${apiKey}`, 'content-type': 'application/json' },
    body: JSON.stringify({ model: env.MODEL_NAME || (provider === 'glm' ? 'glm-5.3' : 'wangsu/gpt-5.5'), messages, stream: useStream, temperature: 0.2, max_tokens: 1400, ...(provider === 'glm' ? { thinking: { type: 'disabled' } } : {}) }),
    signal: AbortSignal.timeout(20000)
  });
  if (!response.ok) throw new Error(`enterprise_model_${response.status}`);
  if (useStream && response.body) {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let content = '';
    let model = env.MODEL_NAME || 'glm-5.3';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.startsWith('data:')) continue;
        const payload = line.slice(5).trim();
        if (!payload || payload === '[DONE]') continue;
        try { const chunk = JSON.parse(payload); model = chunk.model || model; content += chunk.choices?.[0]?.delta?.content || ''; } catch {}
      }
    }
    if (!content) throw new Error('enterprise_model_empty');
    return { content, model, provider };
  }
  const data = await response.json();
  const content = data?.choices?.[0]?.message?.content;
  if (!content) throw new Error('enterprise_model_empty');
  return { content, model: data.model || env.MODEL_NAME || (provider === 'glm' ? 'glm-5.3' : 'wangsu/gpt-5.5'), provider };
}

function parseModelJson(content) {
  try { return JSON.parse(content); } catch {}
  const fenced = String(content).match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fenced) { try { return JSON.parse(fenced[1]); } catch {} }
  return null;
}

const agentSystem = '你是招聘决策与协同助手。遵守：不自动淘汰或录用；不创造学校等级、权重或阈值；缺失证据标为待核证；输出必须可追溯、可解释，并明确结论效力、下一责任人和恢复入口。';

function buildJd(input) {
  const raw = String(input.description || '').trim();
  const title = String(input.title || '').trim() || (raw.includes('架构') ? '数据架构师' : '待确认岗位');
  const must = raw.match(/(?:必须|需要|要求|熟悉|具备)[^。；\n]*/g)?.slice(0, 4) || ['能对岗位关键产出负责（待业务负责人确认）'];
  const risks = [];
  if (!raw) risks.push('缺少岗位原始描述，当前仅能生成岗位假设。');
  if (!input.salary) risks.push('未提供薪资带，无法完成薪资与人才供给张力判断。');
  if (!input.location) risks.push('未提供工作地点，无法完成渠道与可招性判断。');
  if (raw.includes('985') || raw.includes('211') || raw.includes('本科')) risks.push('学历条件需要确认是否与岗位内在产出直接相关，避免把偏好写成硬门槛。');
  return { status: risks.length ? 'limited-evidence' : 'evidence-ready', title, candidateSearchNames: [title, title === '数据架构师' ? '数据架构与治理' : `${title} 专家`], objective: `负责${title}相关业务产出，服务对象与关键协作关系待业务负责人确认。`, mustHave: must, trainable: ['具体业务域知识可在入职后培养', '公司内部流程与系统使用'], preferred: ['有复杂项目从 0 到 1 经验'], channelProjection: { boss: title, zhipin: title === '数据架构师' ? '数据架构 / 数据治理' : title, liepin: title }, risks, nextOwner: '岗位需求负责人确认岗位产出、薪资带与地点' };
}

function assessCandidate(input) {
  const text = String(input.resume || '').trim();
  const role = String(input.role || '数据架构师');
  const matched = [];
  if (/架构|治理|中台|平台/.test(text)) matched.push({ requirement: '数据架构与治理经验', support: '明确支持', evidence: '简历出现架构、治理或平台建设项目', next: '面试核证本人实际负责范围与结果' });
  if (/团队|带领|负责人|管理/.test(text)) matched.push({ requirement: '跨团队协作与推进', support: '部分支持', evidence: '简历出现团队或负责人经历', next: '追问协作对象、约束与复盘' });
  if (/本科|硕士|大学|学院/.test(text)) matched.push({ requirement: '教育事实', support: '部分支持', evidence: '简历包含教育经历，但尚未做外部核验', next: '如有正式规则，再进行岗位相关核验' });
  if (!matched.length) matched.push({ requirement: '岗位关键产出', support: '未提供证据', evidence: '当前材料没有可定位的岗位相关经历', next: '补充项目、职责、结果和时间定位' });
  return { status: matched.some(x => x.support === '未提供证据') ? 'limited-evidence' : 'evidence-ready', role, evidence: matched, highlights: matched.filter(x => x.support === '明确支持').map(x => x.evidence), concerns: matched.filter(x => x.support !== '明确支持').map(x => x.evidence), decisionEffect: '这是逐项证据关系，不是正式总分、淘汰或录用结论。', nextOwner: '招聘人员与用人部门共同核证' };
}

function buildInterview(input) {
  const role = String(input.role || '数据架构师');
  const concern = String(input.concern || '需要核证候选人在复杂项目中的实际负责范围');
  return { status: 'evidence-ready', role, model: '当前未提供正式胜任力模型，以下为建议观察点，不是正式评分锚点。', questions: [
    { competency: '关键产出', question: `请讲一个你亲自负责的${role}项目：当时的业务目标、约束和最终结果是什么？`, followUps: ['你本人做了哪些关键决策？', '结果如何被验证？'], observation: '能否讲清个人行动、约束、结果与复盘。' },
    { competency: '复杂协作', question: '当技术方案与业务、交付或安全要求发生冲突时，你如何推进决策？', followUps: ['谁参与了决策？', '你如何处理未被采纳的方案？'], observation: '能否说明协作对象、取舍依据和后续影响。' },
    { competency: '待核证项', question: concern, followUps: ['请给出具体时间、职责边界和可核验结果。'], observation: '区分亲自完成、参与了解和泛泛表态。' }
  ], nextOwner: '面试官记录岗位相关事实，招聘人员保留核证入口' };
}

async function api(request, url, env) {
  if (request.method === 'GET' && url.pathname === '/api/health') return json({ ok: true, service: 'recruiting-decision-coordinator', version: '0.1.0-mvp' });
  if (request.method === 'GET' && url.pathname === '/api/model-status') { const provider = String(env.MODEL_PROVIDER || 'glm').toLowerCase(); return json({ configured: Boolean(provider === 'glm' ? env.GLM_API_KEY : env.ENTERPRISE_API_KEY), provider, baseUrl: env.MODEL_BASE_URL || (provider === 'glm' ? 'https://open.bigmodel.cn/api/coding/paas/v4' : 'https://aigw.asiainfo.com/v1'), model: env.MODEL_NAME || (provider === 'glm' ? 'glm-5.3' : 'wangsu/gpt-5.5'), secretName: provider === 'glm' ? 'GLM_API_KEY' : 'ENTERPRISE_API_KEY' }); }
  if (request.method === 'GET' && url.pathname === '/api/overview') return json({ metrics: { openRoles: demoRoles.length, pendingCandidates: 86, weeklyInterviews: 18, pendingDecisions: 6 }, roles: demoRoles, candidates: demoCandidates, decisions: [
    { type: 'candidate', candidateId: 'candidate-linxiao', title: '林晓', meta: '数据架构师 · 匹配度 92%', action: '查看证据' },
    { type: 'role', title: '数据架构师', meta: 'JD 草稿 · 技术平台部', action: '审阅建议' },
    { type: 'candidate', candidateId: 'candidate-zhouning', title: '周宁', meta: '产品经理 · 匹配度 88%', action: '查看证据' },
    { type: 'interview', title: '王璐', meta: 'Java 专家 · 面试待确认', action: '确认时段' }
  ] });
  if (request.method !== 'POST') return json({ error: 'method_not_allowed' }, 405);
  const body = await readBody(request);
  if (url.pathname === '/api/jd') {
    const fallback = buildJd(body);
    try {
      const model = await enterpriseChat(env, [{ role: 'system', content: `${agentSystem} 你负责岗位定义与渠道投影。只输出 JSON，不要 Markdown。字段：status,title,candidateSearchNames,objective,mustHave,trainable,preferred,channelProjection,risks,nextOwner。` }, { role: 'user', content: JSON.stringify(body) }]);
      const result = model && parseModelJson(model.content);
      if (result) return json({ ok: true, mode: 'model', model: model.model, result, receipt: { kind: 'draft', createdAt: new Date().toISOString() } });
      if (model) fallback.modelNote = model.content;
    } catch (error) { fallback.modelError = error.name === 'TimeoutError' ? 'enterprise_model_timeout' : error.message; }
    return json({ ok: true, mode: 'fallback', result: fallback, receipt: { kind: 'draft', createdAt: new Date().toISOString() } });
  }
  if (url.pathname === '/api/assess') {
    const fallback = assessCandidate(body);
    try {
      const model = await enterpriseChat(env, [{ role: 'system', content: `${agentSystem} 你负责候选证据评估。只输出 JSON，不要 Markdown。字段：status,role,evidence,highlights,concerns,decisionEffect,nextOwner。evidence 是逐项记录数组，每项含 requirement,support,evidence,next。不要输出正式总分或淘汰结论。` }, { role: 'user', content: JSON.stringify(body) }]);
      const result = model && parseModelJson(model.content);
      if (result) return json({ ok: true, mode: 'model', model: model.model, result, receipt: { kind: 'evidence-assessment', createdAt: new Date().toISOString() } });
      if (model) fallback.modelNote = model.content;
    } catch (error) { fallback.modelError = error.name === 'TimeoutError' ? 'enterprise_model_timeout' : error.message; }
    return json({ ok: true, mode: 'fallback', result: fallback, receipt: { kind: 'evidence-assessment', createdAt: new Date().toISOString() } });
  }
  if (url.pathname === '/api/interview') {
    const fallback = buildInterview(body);
    try {
      const model = await enterpriseChat(env, [{ role: 'system', content: `${agentSystem} 你负责结构化面试设计。只输出 JSON，不要 Markdown。字段：status,role,model,questions,nextOwner。questions 每项含 competency,question,followUps,observation。没有正式胜任力模型时必须写明建议观察点而非正式评分锚点。` }, { role: 'user', content: JSON.stringify(body) }]);
      const result = model && parseModelJson(model.content);
      if (result) return json({ ok: true, mode: 'model', model: model.model, result, receipt: { kind: 'question-pack-draft', createdAt: new Date().toISOString() } });
      if (model) fallback.modelNote = model.content;
    } catch (error) { fallback.modelError = error.name === 'TimeoutError' ? 'enterprise_model_timeout' : error.message; }
    return json({ ok: true, mode: 'fallback', result: fallback, receipt: { kind: 'question-pack-draft', createdAt: new Date().toISOString() } });
  }
  return json({ error: 'not_found' }, 404);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname.startsWith('/api/')) return api(request, url, env);
    return env.ASSETS.fetch(request);
  }
};
