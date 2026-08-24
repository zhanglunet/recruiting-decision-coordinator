# 招聘决策与协同助手

版本：0.1.0

这是一套面向招聘人员／HRBP 的企业领域 Agent 可移植源码。它将岗位定义、候选证据和面试准备组织成一个主 Agent 与三个专业 Skill，并把简历解析、排期、消息和指标计算留在受控运行契约中。

## 它帮助作什么决定

- 把非结构化岗位需求转成可确认 JD，区分必要、可培养和偏好条件，并指出渠道与可招性风险；
- 把候选材料转成逐项岗位证据、亮点、疑点、缺口和核证动作；
- 依据当前岗位产出和胜任力模型生成结构化面试问题；
- 在真实授权和 Tool 装配后，协助处理面试排期、批准范围内的邀约／改约／提醒和招聘指标解释。

主 Agent 不自动淘汰或录用，不自行创设权重、阈值、学校等级或胜任力模型。用人部门保留专业录用责任，招聘人员保留流程与合规责任。

## 源码结构

- `SYSTEM_PROMPT.md`：职业身份、七层联合行为、主 Skill 路由和人工门；
- `skills/shape-job-and-publishing/`：岗位定义与渠道投影；
- `skills/assess-candidate-evidence/`：候选证据评估；
- `skills/design-structured-interview/`：结构化面试设计；
- `contracts/runtime-integrations.md`：六组宿主无关 Tool 与状态契约；
- `evaluation/cases.json`：九类正常与最高风险 fixtures；
- `scripts/`：静态校验、冻结、Source Gate 收据校验、打包和源码安装；
- `tests/`：交付脚本与资产一致性测试。

## 典型使用

```text
把这段岗位需求整理成可确认 JD，并指出薪资与条件张力。
```

```text
按岗位标准逐项整理这份简历证据；没有正式聚合规则，不要打总分。
```

```text
依据当前胜任力模型和候选待核证项，生成结构化面试问题。
```

输入正式判断前，应提供可识别的岗位对象、当前标准及其身份／版本／范围／责任人。候选任务还需要原材料或可定位的解析结果；面试任务若要使用正式评分锚点，需要当前胜任力模型。缺少这些事实时，Agent 会交付有限结果和恢复入口，而不是猜测。

## 运行装配

所有目标平台能力当前是 `required_not_connected`，`tool_evidence_status = none`。`contracts/runtime-integrations.md` 只定义业务目的、授权、副作用、结果效力、部分成功和恢复语义；平台适配者仍需依据目标系统的官方文档和真实权限实现适配。

源码中的模拟 Tool 返回只用于设计回放，不证明 ATS、渠道、学校核验、日历、会议室、消息或看板已经连通。目标平台接入后仍需验证真实对象身份、权限、收据、部分成功和恢复。

## 验证

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
```

静态验证通过只证明文件、版本、引用和关键安全边界一致。九类 fixture 当前状态为 `designed_not_run`，不构成目标模型行为证据。

## Source Gate 与打包

完整源码必须先生成冻结快照，再由新的隔离评审者执行 Source Gate。只有结构有效、结论为 `pass` 且 `reviewed_snapshot_id` 与当前源码一致的收据，才允许 `package_release.py` 生成 ZIP。冻结后任何源码变化都会使旧收据失效。

## 源码安装

`install_local.py` 将通过门禁的 ZIP 安装到显式绝对目录，拒绝覆盖已存在目标，并写入文件哈希收据。源码安装只证明资产可达、完整、可回读，不等于平台激活、Agent 已注册、Tool 已连接或行为已验证。

推荐使用带版本的目标，例如：

```text
/Users/john/.codex/enterprise-agents/recruiting-decision-coordinator-0.1.0
```

该目录是本机便携源码存放位置，不是 Codex 官方运行时注册声明。

## 已知限制

- 尚无目标平台适配器、租户权限或真实 Tool 收据；
- 尚未在目标模型运行九类评测；
- 没有企业正式聚合规则时不提供正式分数或排序；
- 没有可比口径时不直接比较渠道指标；
- 外部法律、组织政策和平台能力变化时，应重新核证适用边界。

## 回滚

安装器不覆盖现有目录。回滚时仅移走或删除本次精确版本目录，并保留 ZIP、SHA-256 与 `.installation-receipt.json` 供核对；不要触碰其他 Agent、Skills 或全局配置。
