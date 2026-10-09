我结合仓库中的产品说明、工作流、权限、集成文档，以及关键 Jira 原始记录，按 **“项目定位 → 架构 → 数据流 → 技术难点 → 面试提问”** 来梳理。

先说明一个重要前提：

> **当前仓库是 Curate 的知识库，不是完整业务源码仓库。**  
> 可以较可靠地分析业务规则和已记录的设计，但不能据此确认所有底层实现、生产部署状态或性能指标。尤其架构总览明确标注了“服务名为示意、部分基础设施待核实”。

下面会区分“文档有依据的事实”和“面试中应进一步讨论的设计问题”。

---

# 一、宏观上，这个项目在做什么？

## 1. 一句话定位

**Curate 是面向学术出版机构的“专题策划、提案审核与专刊生命周期管理平台”。**

原名是 **SIMT：Special Issue Management Tool**，正在使用 **Research Exchange Curate** 品牌。

它连接外部学者、期刊编辑、出版运营人员，以及身份、投稿审稿、出版展示和数据分析系统。

可以将它理解为：

> 把“某个学者提出一个专题想法”，转化为“经过审核、组织征稿、跟踪稿件、最终出版的专刊”的业务协作系统。

依据：[产品概览](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/overview.md#L3-L15)。

## 2. 用一个例子理解业务

假设某位学者希望在某本期刊上组织一个“人工智能辅助药物研发”的专刊。

整个过程大致是：

1. 提交专题提案，包括标题、研究范围、拟邀请的客座编辑等。
2. 出版方检查专题质量、客座编辑情况、期刊适配性。
3. 必要时邀请编委、期刊编辑提供评审意见。
4. 要求修改、拒绝，或者接受提案。
5. 接受后创建正式专刊。
6. 配置征稿方式、开放日期、截止日期等。
7. 投稿与审稿系统持续反馈稿件状态。
8. 运营人员跟踪专刊进展、处理延期、完成出版登记。
9. 数据提供给报表、营销和出版展示等下游系统。

**这里管理的是“组织一个专题出版项目”，而不是独立实现完整的论文投稿、审稿和出版系统。**

## 3. 两个最核心的业务对象

| 对象 | 含义 | 主要解决的问题 |
|---|---|---|
| **SIP：Special Issue Proposal** | 专刊提案 | 这个专题是否值得做？由谁负责？是否符合要求？ |
| **SI：Special Issue** | 正式专刊 | 已批准的专题如何启动、征稿、跟踪与完成？ |

两者不是简单改一下状态：

- SIP 更关注**提案、筛查、意见、决策**。
- SI 更关注**征稿安排、稿件进度、运营与出版状态**。
- 在 SCA/CDS 的跨期刊场景中，一份提案可能创建多个 SI。
- Generic SIP 的相关 MVP 则不包含多期刊专辑创建。

这意味着它本质上包含两个相互衔接、但职责不同的业务域。

## 4. 主要参与者

| 角色 | 业务职责 |
|---|---|
| Guest Editor，GE | 客座编辑，参与提案、修改与专题组织 |
| Lead GE | 主要客座编辑，承担特定修改和确认职责 |
| Proposal Manager | 管理 Generic 提案流程 |
| Journal Manager | 管理所分配期刊的 Generic SI |
| Operations Lead | SCA/CDS 工作流中的运营负责人 |
| Screener | 完成筛查检查表 |
| Commissioning Editor，CE | 委约编辑，参与提案决策与协调 |
| Journal Editor，JE | 期刊编辑，提供期刊层面的评审或决策 |
| Editorial Board Member，EBM | 编委，参与提案评审 |
| Tenant / Platform Admin | 管理租户、用户、权限和配置 |

**项目复杂度主要不是来自表单数量，而是同一份数据在不同角色、阶段、期刊和租户下，有不同的操作规则。**

---

# 二、业务架构：不是一条流程，而是多套流程并存

## 1. Generic 和 SCA/CDS 必须分开理解

### Generic SIP：相对通用的提案流程

```text
Ideation：构思
    ↓
Screening：筛查
    ↓
Review：评审
    ↓
Accepted：接受
    ↓
满足条件后创建 Generic SI

流程中还存在：
Revision：修改
Rejected：拒绝
Withdrawn：撤回
```

重要细节：

- Screening 检查表未完成，不能做后续决策。
- 筛查完成后新增 GE，相关检查需要重新完成。
- Revision 需要记录来源阶段，以便返回。
- Accepted 后必须经过 **72 小时**，才能创建 SI。
- 72 小时按实际小时计算，不是三个工作日。
- Generic SIP 创建 SI 后，MVP 中仍保持 Accepted，不新增单独的 Acquired 阶段。

### SCA/CDS SIP：更细分的运营流程

```text
SSIP：内部发起 → Ideation ─┐
                         ├→ Submitted → Initial Review
USIP：外部主动提交 ────────┘                  ↓
                           按 Flow、角色及决策分支流转
                           CE / EBM / JE / Publisher 等环节
                                           ↓
                                      Mutual Accept
                                           ↓
                                      SI Acquisition
```

注意：**CE、EBM、JE、Publisher 并不是所有提案都必须严格串行经过的固定步骤。**

这里的两个维度也不要混淆：

- **Generic / SCA-CDS**：工作流体系。
- **SSIP / USIP**：提案来源，分别是邀约型与主动提交型。

依据：[Generic SIP 工作流](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/special-issue-proposals/sip-workflow-generic.md)、[SCA/CDS SIP 工作流](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/special-issue-proposals/sip-workflow-sca-cds.md)。

## 2. Generic SI 的主流程

```text
Draft
  ↓
Acquired
  ↓  到开放日期，或手动 Launch SI
Submission and Review
  ↓  截止日期触发关闭
Closed
  ↓  用户确认已出版
Published
```

额外路径：

- 特定阶段可以进入 Shelved，表示搁置。
- Closed 后延长征稿截止日期，可以回到 Submission and Review。
- SCA/CDS SI 还具有 Paper Commission、Production 等不同阶段，不能直接套用 Generic 的状态图。

**因此，项目不是单向审批流，而是包含回退、分支、定时转换、人工决策与外部事件的业务状态系统。**

依据：[SI 生命周期](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/special-issues/si-lifecycle-and-stages.md#L13-L140)。

---

# 三、技术架构：如何划分职责？

## 1. 先区分“已记录设计”和“待核实技术栈”

| 信息 | 当前仓库能支持到什么程度 |
|---|---|
| 使用 Kafka 进行跨系统事件集成 | 有具体事件、Topic 和 Jira 依据 |
| Generic SI 从原 SI 服务拆分 | 有模块、API、数据库层及定时任务拆分记录 |
| Generic SIP 初始化独立微服务 | 工作流文档有明确记录 |
| CONNECT 负责身份认证和身份数据 | 有具体登录、绑定和同步规则 |
| 租户品牌资源存放在 S3 | 有明确记录 |
| Spring Cloud、Gateway、Kubernetes | 架构总览有描述，但总览标为待进一步验证 |
| PostgreSQL、每租户 Schema、Eureka、Config Server、独立报表读库 | 不能仅凭该总览认定为当前生产实现 |

尤其不要把总览中的 `curate-api`、`curate-reporting` 等示意名称，当作已核验的真实服务清单。

依据：[架构总览及置信度说明](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/architecture.md#L7-L70)。

## 2. 更可靠的逻辑架构图

下面展示的是职责关系，**不是逐个 Pod 的真实部署图**：

```text
                    用户浏览器
            外部学者 / 编辑 / 运营 / 管理员
                         │
                CONNECT 登录认证
                         │
                  Web 页面与 API
                         │
              身份、租户、权限上下文
                         │
        ┌────────────────┼──────────────────┐
        │                │                  │
   SIP 提案业务       SI 专刊业务       共享业务能力
   Generic / SCA      Generic / SCA     GE、期刊、配置
   筛查与评审         创建与征稿         邮件、历史、报表
        │                │                  │
        └────────────────┼──────────────────┘
                         │
                 持久化与异步事件
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
    CONNECT            ReX              STEP
    用户身份        投稿与审稿结果       期刊产品数据
                         │
               SI API / Kafka 出站事件
                         │
                 Snowflake / WOL 等
```

AI Screening、Auto-Tagger、PKG Editor Suggestion 则为业务流程提供辅助筛查、关键词和编辑推荐能力。

## 3. 服务拆分的实际案例：Generic SI

文档记录，Generic SI 从原来的 `si-service` 中拆出，形成独立服务，并包含：

| 模块 | 作用 |
|---|---|
| `generic-si-app` | 主应用，独立部署 |
| `generic-si-common` | 共享公共库 |
| `generic-si-api` | API 契约库 |

拆分不只是改路由，而是覆盖：

- Controller 层。
- Service 层。
- 数据库层。
- 定时任务。
- 部署流水线。

API 也从旧 SI 服务入口迁移到 Generic SI 服务入口。

这类拆分的架构价值是：

> 避免两套业务流程长期共享实现、数据和任务调度，让它们可以独立演进。

代价则是：

- 公共能力如何复用。
- 跨服务一致性如何处理。
- API 契约如何兼容。
- 数据和任务迁移如何避免遗漏。

这些代价是面试讨论点，仓库没有完整交代所有实现方案。

依据：[Generic SI 服务拆分](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/platform/multi-tenancy-and-tenant-id.md#L14-L78)。

## 4. 权限架构：角色不等于最终权限

这个项目更适合用以下逻辑理解授权：

> **是否允许操作 = 租户范围 ∩ 权限点 ∩ 期刊/记录范围 ∩ 当前阶段 ∩ 字段规则。**

例如：

- 有 `sip:write-ops`，不意味着可以操作任何提案。
- 操作 EBM Review Panel，还需要是该 SIP 的 Ops Lead，而且处于 EBM Review 阶段。
- Lead GE 的修改权限与 Revision 阶段相关。
- Journal Manager 只管理分配给自己的期刊。
- SCA/CDS SI Acquisition 要同时满足三项权限：
  `sip:write-ops`、`ge:write`、`si:write-ops`。

所以可以将它描述为：

**角色权限控制，叠加数据范围与业务上下文约束。**

但不能直接声称系统使用了某种具体 ABAC 框架；仓库展示的是行为规则，而非授权引擎实现。

依据：[权限矩阵](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/access-control/permissions-matrix.md#L11-L170)。

## 5. 多租户不是“每张表加个 tenantId”这么简单

仓库体现的租户相关设计包括：

- 用户访问范围隔离。
- 租户品牌、CONNECT 配置等差异。
- S3 资源按租户目录组织。
- Generic / SCA 业务服务与数据分离。
- 外部事件的租户过滤。

一个明确例子：

**消费 STEP Product API 的 Kafka 消息时，只根据消息 Header 中的 Wiley Tenant ID 判断是否处理。**

但要注意：

- 这是特定消费链路的规则，不代表所有消费者都采用同一固定租户过滤。
- Generic/SCA 服务拆分，也不等于“每个租户独立部署一套服务”。
- 当前材料不足以确认所有数据均采用每租户独立 Schema。

---

# 四、整个数据流是怎样的？

与其画一条大箭头，不如拆成六条关键链路。

## 数据流一：用户登录与身份同步

```text
管理员创建本地用户
        ↓
用户点击激活链接
        ↓
跳转 CONNECT 登录
        ↓
返回 Curate
        ↓
按文档规定匹配本地账户，并补充 CONNECT ID
```

后续身份变化走另一条链：

```text
用户在 CONNECT 修改资料
        ↓
CONNECT 发布 Kafka 更新事件
        ↓
Curate 消费事件
        ↓
更新本地身份字段
        ↓
页面展示新信息
```

文档中的两个 Topic：

- `wly.glb.connect.user.updates`
  - 姓名、邮箱。
  - GE 还包含称谓、次邮箱等。
- `wly.glb.connect.userprofile2.updates`
  - GE 的机构信息。

架构重点：

1. **CONNECT 是身份主数据源。**
2. Curate 负责本系统中的角色和业务关系。
3. 管理员创建普通用户，并不等于 CONNECT 自动开通全部业务账户。
4. 身份更新要求失败时不产生部分字段更新。
5. 两个 Topic 的存在，不足以证明跨 Topic 更新具有一个全局事务。

另外，这部分新同步能力在仓库来源中有 Ready for UAT、In QA 状态，**不能直接等同于全部生产环境已上线**。

依据：[CONNECT 集成](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/user-and-system/user-profile-and-connect.md#L15-L119)。

## 数据流二：提案提交、筛查与审核

```text
用户提交提案
    ↓
检查身份、期刊范围、字段和业务条件
    ↓
形成 SIP 记录及当前阶段
    ↓
筛查与评审
    ├── 检查表
    ├── AI Screening
    ├── Auto-Tagger
    └── EBM / JE 等人工意见
    ↓
授权人员提交决策
    ↓
更新阶段、负责人、历史记录
    ↓
按相应规则发送事件、邮件
```

已记录的 SIP 出站事件包括：

- Creation：提交提案。
- Update：字段、阶段、负责人、GE、评审等变化。
- Deletion：相关 SIP 进入 Shelved。

这里有个很值得面试追问的点：

> **Deletion 是集成事件语义，不应自动理解为数据库物理删除。**

另外，PKG 推荐编辑链路不是“拿到推荐结果就能邀请”：

```text
提案标题、范围、目标期刊
        ↓
PKG 推荐符合期刊约束的编辑
        ↓
通过 CONNECT / 平台数据补充邮箱等资料
        ↓
判断是否可邀请
        ↓
发送邀请并记录状态
```

文档明确：

- 缺机构信息，仍可以展示候选人。
- 缺邮箱，不能放入可邀请集合。
- PKG 本身不是邮箱来源。

依据：[事件集成](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/platform/integrations-and-events.md#L13-L46)、[编辑推荐](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/special-issue-proposals/sip-overview.md#L17-L39)。

## 数据流三：SIP 异步转为 SI——最有技术含量的链路之一

仓库记录了一个实际问题：

> 跨期刊 Acquisition 可能一次创建超过 200 个 SI，处理耗时数分钟；前端等待超时后，用户重复点击，造成重复创建。

改造后的设计是：

```text
用户确认 Acquisition
        ↓
保存创建请求数据
        ↓
SIP → Complete-Acquired - In Progress
        ↓
发送内部消息，快速返回
        ↓
SI 服务消费消息
        ↓
后台创建一个或多个 SI
        ├── 成功 → Complete-Acquired
        │          Process Log 展示 SI Code
        └── 失败 → Complete-Acquired - Failed
```

关键理解：

- 接口快速成功返回，表示**请求被受理**，不是全部 SI 已创建成功。
- 中间态既是用户可见进度，也是重复请求拦截依据。
- 异步化解决长耗时等待问题。
- 但是“异步化 + 前端按钮禁用”本身不能证明端到端幂等。

还需要进一步确认：

- 并发点击时阶段更新是否原子。
- 消息重复投递是否重复创建。
- 部分期刊已成功、部分失败时如何重试。
- 数据落库后消息未发出时如何恢复。

这些实现细节，仓库没有完整给出。

依据：[原始 Jira CT-11064](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/raw/jira/phase-3/CT-11041-simt-improvements-2/CT-11064-solution-to-stop-users-from-creating-duplicate-sis-during-si-acquisition.md#L13-L34)。

## 数据流四：SI 开放征稿与稿件状态回流

```text
SI 达到开放日期，或人工 Launch
        ↓
更新业务阶段，发出 SI Open 事件
        ↓
外部投稿审稿流程运行
        ↓
ReX 发布稿件事件
        ↓
Curate 消费并更新 Submission Overview
```

回流事件不止：

- Submitted
- Accepted
- Rejected

后续需求还覆盖：

- Withdraw。
- Return to Draft。
- Refuse to Consider。
- Rescind Decision。

例如：

| 事件场景 | 文档规定的统计变化 |
|---|---|
| 已接受稿件后来撤回 | 从 Accepted 转到 Withdrawn |
| Return to Draft | 从 Submitted 计数移除 |
| 再次提交 | 重新计入 Submitted |
| 撤销拒绝决定 | 回到 Submitted 等待后续决定 |

所以这里的关键不是简单的“收到一个事件就计数 +1”，而是：

**按照稿件状态变化维护正确的业务统计。**

还要区分：

- SI 的内部业务阶段。
- 是否开放投稿。
- 单篇稿件状态。
- 对外事件中的 State。

它们有关联，但不是同一个字段。

依据：[SI 稿件状态回流](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/special-issues/si-lifecycle-and-stages.md#L520-L551)、[ReX 集成与事件演进](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/platform/integrations-and-events.md#L196-L213)。

## 数据流五：报表和下游数据

有两类不同数据流：

### 运营报表

```text
SIP 当前状态 / 阶段历史
          ↓
Pipeline / Chase Tracker / TAT
          ↓
页面查询、筛选、导出
```

不能把它们一概说成实时：

- Pipeline 是当前阶段分布快照。
- TAT 每天通过定时任务计算。
- TAT 使用**中位数**，不是平均值。
- 修改阶段耗时从原审核阶段扣除，单独统计。
- 跨月完成按完成月份归属。
- 重复进入阶段要按规则累计。

### 外部营销与出版消费

```text
SI Events API
      ↓
Snowflake
      ↓
Marketing
```

Curate API 的部分 SI 指导信息也提供给 WOL 使用。

这里最重要的是**数据归属**：

- Curate 管理专题与提案业务。
- CONNECT 管理身份。
- ReX 管理稿件决策。
- WOL 等系统拥有部分正式出版数据。

文档中已经记录：某些出版日期、出版链接相关字段因为 Curate 不是数据所有者而从出站 API 中移除。

**“页面能填写或展示某个字段”不代表“有资格把它作为权威数据发布给所有下游”。**

依据：[TAT 报表](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/reporting/sip-tat-reporting.md#L120-L155)、[出站数据及字段移除](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/product/features/platform/integrations-and-events.md#L78-L147)。

## 数据流六：当前知识库自身的流程

当前仓库运行的是另一条链：

```text
Jira / Confluence 原始资料
            ↓
Python 导出脚本
            ↓
原始输入层
            ↓
AI 辅助整理、人工审核
            ↓
产品知识页面
            ↓
MkDocs 构建
            ↓
GitHub Pages
```

当前状态需要特别说明：

- 自动导出工作流设置了 `if: false`，处于禁用状态。
- MkDocs 发布工作流可由匹配的主分支变更或手动触发。
- 这套文档发布流水线，**不是 Curate 业务微服务的部署流水线**。

依据：[知识库贡献方式](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/CONTRIBUTING.md#L7-L27)、[禁用的导出工作流](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/.github/workflows/export-and-ingest.yml#L1-L35)、[文档发布工作流](/home/runner/work/CTC-Curate-Knowledge/CTC-Curate-Knowledge/.github/workflows/mkdocs-gh-pages.yml)。

---

# 五、这个项目真正值得讲的技术难点

如果面试介绍只是“Spring Cloud + Kafka + 数据库”，价值不大。更值得讲的是：

| 难点 | 为什么复杂 |
|---|---|
| 多工作流状态管理 | Generic 与 SCA/CDS 不同，且有回退、分支和来源阶段 |
| 上下文权限 | 同样角色在不同租户、期刊、记录和阶段下权限不同 |
| 异步 Acquisition | 长耗时、批量创建、重复点击、消息重复和部分失败 |
| 多系统主数据归属 | 身份、稿件、期刊、出版信息分别属于不同系统 |
| 事件驱动统计 | 撤回、撤销决定、退回草稿会修正已有统计 |
| 定时任务一致性 | 手动 Launch 与自动任务可能竞争；延期会改变后续行为 |
| 业务统计口径 | TAT 需要处理修订中断、重复进入、跨月及中位数 |
| 服务拆分迁移 | 不能只迁移接口，还要迁移数据、权限、任务及部署 |

**这个项目的本质复杂度，是业务规则与分布式一致性交织，而不是单纯的高并发。**

仓库没有提供真实 QPS、数据规模、延迟分位数或可用性指标，面试时不应编造。

---

# 六、如果我是面试官，会具体问什么？

下面每题都给出“我想考察什么”和“回答应覆盖什么”。其中幂等、事务、重试等属于应讨论的设计要点，不代表仓库已证明采用了这些方案。

## A. 业务理解

### 1. SIP 和 SI 为什么要分开，而不是同一张表加一个状态？

**考察：领域建模。**

回答重点：

- 一个是提案决策对象，一个是专刊运营对象。
- 生命周期、字段、责任人和权限不同。
- SIP 的审核记录需要独立保留。
- 跨期刊 Acquisition 可能产生多个 SI，不能假定永远一对一。

### 2. Curate 和 ReX Review 的边界是什么？

**考察：是否真正理解系统职责。**

回答重点：

- Curate 管专题提案与专刊组织。
- ReX 管投稿和稿件评审。
- Curate 消费稿件事件并展示进度，不应成为稿件决策的另一套权威来源。

### 3. Generic 与 SCA/CDS 有哪些本质差异？

**考察：能否避免把不同流程混成一套。**

回答重点：

- 参与角色不同。
- 阶段及决策路径不同。
- 权限和创建条件不同。
- Generic SIP 的 72 小时等待和 SCA/CDS 的异步 Acquisition，不应混讲。

### 4. 项目效果应该如何衡量？

**考察：是否从业务价值出发。**

合理指标包括：

- 提案到 SI Launch 的耗时。
- 各阶段 TAT。
- 提案积压与催办数量。
- Acquisition 重复创建率、失败率。
- 数据同步延迟及人工修正量。

但要明确：哪些是实际测量过的，哪些只是建议观察的指标。

## B. 架构与权限

### 5. 为什么要把 Generic SI 拆成独立服务？

**考察：服务拆分是否基于业务边界。**

回答重点：

- 两套流程独立演进。
- 数据与定时任务需要隔离。
- 独立部署降低相互影响。
- 同时增加契约管理、共享能力维护和运维成本。

追问很可能是：

> 不拆服务，只拆模块是否足够？你的拆分依据是什么？

### 6. 用户有 `sip:write-ops`，为什么仍然不能操作某个 SIP？

**考察：数据权限与上下文权限。**

回答重点：

- 是否在正确租户。
- 是否为该记录的负责人。
- 是否处于允许操作的阶段。
- 是否满足其他组合权限。
- 前端按钮隐藏与后端接口授权必须一致。

### 7. CONNECT 已经做了登录，为什么 Curate 还需要授权体系？

**考察：认证与授权的区别。**

回答重点：

- CONNECT 回答“你是谁”。
- Curate 回答“你能操作哪些期刊、提案、字段与决策”。
- 登录成功不能绕过租户和记录范围限制。

### 8. 怎么证明没有跨租户数据泄露？

**考察：租户隔离是否覆盖完整链路。**

我会追问：

- 用户能否通过直接修改记录 ID 越权？
- 租户上下文来自可信身份还是可伪造 Header？
- 列表、详情、导出是否都隔离？
- Kafka 消费、定时任务、缓存和附件是否隔离？

不要只回答“SQL 加了 tenantId”。

## C. 异步与一致性

### 9. Acquisition 改成异步，具体解决了什么问题？

**考察：是否理解真实故障背景。**

回答应覆盖：

- 多 SI 创建耗时长。
- HTTP 等待超时导致重复点击。
- 异步受理使请求快速返回。
- 中间态展示进度并阻止重复操作。
- 最终完成状态与接口受理状态分离。

### 10. 两个 Acquisition 请求同时到达，怎么办？

**考察：并发正确性。**

我不会接受“禁用按钮”作为完整答案。

应讨论：

- 阶段检查与更新是否原子。
- 是否存在业务幂等键。
- 数据库唯一约束是否兜底。
- 并发失败时给用户什么响应。

### 11. Kafka 消息重复投递，会不会重复创建 SI？

**考察：消费幂等。**

应讨论：

- 如何标识同一个业务请求。
- 如何标识同一次 Acquisition 下某一期刊的 SI。
- 消费成功但确认消息前崩溃会怎样。
- 重放是否会重复发送邮件和出站事件。

### 12. 数据库已写入，但消息发送失败怎么办？

**考察：数据库与消息系统的一致性。**

回答重点是先说明实际方案，再解释其可靠性。

可讨论事务性发件箱、可靠重试、补偿与对账等选择，但不能未经核验就说项目用了 Outbox。

### 13. 200 个 SI 中有 150 个成功，剩余失败，如何恢复？

**考察：批量任务与部分失败。**

应覆盖：

- 是否记录子任务结果。
- 重试是否只处理失败项。
- 已成功项是否会重复创建。
- 总任务什么时候才算完成。
- 用户如何看见失败原因。

### 14. 同一稿件的事件乱序，会不会把 Accepted 错误覆盖成 Submitted？

**考察：事件顺序与状态正确性。**

应讨论：

- 稿件身份键。
- 版本或事件顺序依据。
- 合法状态转换。
- 重复、迟到及撤销事件。
- 历史重放与对账。

只说“Kafka 保证顺序”不够；还需要说明分区键、消费者和不同 Topic 的边界。

## D. 工作流、时间与主数据

### 15. 为什么 Revision 要记录来源阶段？

**考察：状态机建模。**

回答重点：

- 修改可能来自不同审核环节。
- 返回路径不同。
- 修改取消或提交后的负责人不同。
- TAT 必须知道哪些时间属于修改，哪些属于原阶段。

### 16. 手动 Launch 与自动开放任务同时执行会怎样？

**考察：定时任务竞争。**

应讨论：

- 同一 SI 是否只允许一次有效转换。
- SI Open 事件是否重复。
- 邮件是否重复。
- 多实例定时任务及任务重试如何处理。

### 17. “72 小时”和“5 个工作日”如何测试？

**考察：时间规则是否精确。**

应覆盖：

- 精确时间戳与日期的区别。
- 时区与夏令时。
- 周末、节假日口径。
- 临界点前一秒、正好到点、后一秒。
- 系统使用客户端时间还是服务端时间。

项目里存在多处日期规则，不能统一用“加几天”处理。

### 18. 用户邮箱变了，如何避免创建一个重复用户？

**考察：身份绑定稳定性。**

回答重点：

- 区分首次基于邮箱匹配与已有 CONNECT ID 后的同步。
- 业务关系应该如何保留。
- 重复、迟到身份事件如何处理。
- 同步失败是否造成部分字段更新。

### 19. 为什么某些出版字段要从 API 删除，但页面仍可能有它们？

**考察：主数据归属。**

回答重点：

- 本地录入值不必然是权威出版事实。
- 下游依赖的数据应有明确所有者。
- 删除字段还涉及契约兼容、消费者迁移和版本管理。

## E. 报表、AI 与测试

### 20. TAT 为什么不能直接用“最后更新时间减创建时间”？

**考察：统计口径。**

回答重点：

- 要识别具体阶段进入和退出。
- 排除 Revision 耗时。
- 累加重复进入阶段的有效时间。
- 按完成月份归属。
- 最终指标是中位数，不是平均值。

### 21. EBM 推荐服务返回一个没有邮箱的专家，你会如何处理？

**考察：跨系统数据质量和降级行为。**

项目文档中的答案很具体：

- 缺机构：仍可展示。
- 缺邮箱：不能邀请。
- 推荐为空与服务异常要区分。
- 只推荐目标期刊相关的编辑。
- PKG 不提供邮箱，需要其他数据来源补齐。

### 22. 新增一个 GE，为什么可能让已经完成的检查表失效？

**考察：关联数据变化对业务前置条件的影响。**

回答重点：

- 原检查结果对应旧的 GE 集合。
- 新增成员引入新的待筛查对象。
- 检查完成状态不是永远有效的布尔值。
- 必须重新验证后才能继续决策。

### 23. 如果你负责 QA，会优先测试哪几类场景？

**考察：风险驱动测试能力。**

我会期待至少覆盖以下矩阵：

| 测试维度 | 具体场景 |
|---|---|
| 工作流 | Generic / SCA-CDS、允许和禁止的状态转换 |
| 权限 | 正确角色但错误负责人、错误期刊、错误租户 |
| 并发 | 重复点击 Acquisition、两个浏览器同时提交 |
| 消息 | 重复、乱序、延迟、格式错误、租户不匹配 |
| 批量失败 | 部分 SI 创建失败后重试 |
| 时间 | 72 小时边界、工作日、截止日期、延期 |
| 一致性 | 状态变化与日志、邮件、事件、报表是否匹配 |
| 身份 | 邮箱更改、CONNECT ID 绑定、同步失败 |
| 数据展示 | 页面隐藏字段是否仍被错误导出或发布 |
| 迁移回归 | 新旧服务路由、存量数据、定时任务归属 |

高质量测试不只是检查“页面显示成功”，还要检查**最终数据状态和副作用是否恰好正确**。

### 24. 文档、Jira 与实际系统不一致时，你怎么办？

**考察：需求分析和证据意识。**

这个仓库确实存在需要厘清的地方，例如：

- Generic Review 一处写 GE 区域只读、未来支持邀请；另一处又描述 Review 阶段可邀请。
- 日期规则有自然日、工作日及不同阶段条件。
- 较早 ReX 集成说明较窄，后续又增加拒绝、撤回和撤销相关事件。
- 部分标为 Verified 的文档，来源 Story 当时仍在 QA/UAT。

好的回答不是随便选择其中一条，而是：

> 明确工作流、版本和环境，追溯对应 Story 与验收标准，再通过实现和测试确认当前有效规则。

---

# 七、面试中如何概括这个项目？

可以用下面这段作为项目介绍基础，但要把“个人贡献”换成你真实做过的内容：

> Curate 是面向学术出版机构的专题提案与专刊生命周期管理平台。它将外部学者提交的专题想法，通过筛查、评审和修改转化为正式专刊，并与身份、投稿审稿和出版数据系统集成。  
>
> 项目同时支持 Generic 和 SCA/CDS 两套工作流，权限不仅由角色决定，还取决于租户、期刊范围、记录负责人和业务阶段。系统通过 API 处理交互操作，通过 Kafka 完成身份同步、稿件事件回流和对外数据发布。  
>
> 其中比较有代表性的技术问题，是跨期刊批量创建 SI 导致请求超时与重复创建，因此引入了异步 Acquisition、中间状态和重复请求控制。另一个难点是外部稿件状态变化、工作流回退和统计口径之间的一致性。

**最值得深入准备的三个专题是：**

1. **异步 Acquisition：长耗时、幂等、并发与部分失败。**
2. **多维权限：租户、期刊、负责人、阶段与字段级约束。**
3. **事件一致性：稿件状态回流、主数据归属与统计口径。**

把这三个专题讲透，比罗列技术栈更能体现你对项目的理解。