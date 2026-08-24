# 招聘指挥台 UI 原型

这是招聘决策协调 Agent 的独立前端原型，使用演示数据展示岗位诊断、候选人证据、面试排期和招聘数据看板。

## 本地运行

```bash
cd /Users/john/recruiting-decision-coordinator
python3 -m http.server 4173 --directory ui
```

然后打开 <http://127.0.0.1:4173>。

当前版本不连接真实 ATS、日历或消息服务；所有“AI 建议”动作均为可替换的交互占位，界面已明确标注演示数据。
