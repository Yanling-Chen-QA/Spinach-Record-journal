# 1st Week
# Day1 (26-04-20)
### todo
- [x] sso、2FA概念
- [x] 带笔、**拓展坞、键盘电池**、圆孔耳机
### done
- 拉取各个账户权限，初步了解公司体系
- standup meeting 听取了几个项目关键词


# Day2 (26-04-21)
### todo
- [x] Workday onboarding 课程学习
- [x] 15秒英文自我介绍:Hi everyone, my name is YanLing Chen. I’m a student from East China Normal University. I’m very happy to be here as an intern, and I look forward to learning from all of you. Thank you!
- [x] 拿员工卡（等待物流中）
- [ ] Wiley各个内部服务及系统：jira、confluence、jsm、workday、outlook、teams、GitHub、内部应用商店（关于内部系统是如何隔开的，微软给了公司配套sso，很有意思想知道怎么设计的）
- [x] Clarity工单-隶属项目名称（项目名称）
- [ ] Smit-auto项目架构学习（初步）：
    1.	Cursor-agent学习-guide文档
    2.	把不知道/想知道的知识点记录下来
    3.  由于自动化测试涉及到simt系统，所以要学习wiley的业务线


### done
- 对公司系统有了比较多的了解，可以做成思维导图/总结文字
- 项目相关的工具准备到位，代码已拉下进行学习
- 了解自动化测试项目vs开发项目的异同
- 领取当前的任务是research一些cursor里如何用sills写好rules


# Day3 (26-04-22)
### todo
- [ ] 思考除了journal，哪些项目or东西需要单开一个文件记录，以及具体的记录形式应该是什么样的
- [ ] 调研rules和skills
- [x] 询问公司所有能用的工具还有哪些（AI向）
### done
- 课程培训看完，非常尊重人的企业文化
- 今天各地的研发团队开会了，是全英文的挺好的，很好练习口语；以及大概看了一下公司的项目，是有一些是很感兴趣的，以后多接触se的人来偷简历
- 今天开始随机调研了一些skill和rule的内容，先从官方文档/国外小红书（reddit）开始，然后搜索相关文献，这里我觉得可以做成标准的sop来为以后调研某一个新东西提供帮助，研究一下这个agent吧，真的非常有用啊
- 领取新的调研任务：llm-wiki，看了一下是一个很有意思的方向，不知道能不能作为专利写出来

# Day4 (26-04-24)
### todo
- [x] llm-wiki调研
- [x] Atlassian的mcp配置以及使用，参考写一下脚本
- [ ] 需要把公司每一步的it相关内容了解一下，我太好奇了

### done
- [llm-wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)是什么概念了解了，后续看一下别人以及自己如何实现
- [mcp](https://www.geekpm.com/archives/mcp-fuctioncalling)概念有了更清晰的认知，需要更多的学习ai
- cursor配置atlassian的官方mcp，看了对应文档后简单使用了一下

# Done List
- llm-wiki概念学习+参考学习一些具体实现的项目
- 解决ip跳回国内导致的copilot以及其他ai被限制
- cursor配置atlassian的官方mcp，看了对应文档后简单使用了一下
- ocr工具了解


# 2nd Week
# Day5 (26-04-27)
### todo
- [x] 读llm-wiki应用在wiley知识库的设计文档
- [x] 写拉取jira中story的脚本
### done
- 读了设计文档，如果在理解好业务的情况下，和ai交流会很有效果
- 用cursor写了脚本，看来要稍微再学习一下python了，不然都看不懂。先配置Atlassian的token，然后有了权限之后，就可以在cursor类工具中配置相关的mcp，然后就可以使用这个工具，我对于它的实现很好奇，我很想知道怎么完成的


# Day6 (26-04-29)

### ideas
- 需要每天给自己找个目标，不然上班这么久的时间效率却这么低
### todo
- [x] 读llm-wiki应用在wiley知识库的设计文档
- [x] 阅读脚本文件内容
- [x] 调整一下原脚本的代码，以及再梳理一下需求重构代码
- [x] token数量有限制，意味着需要学习一下如何省着用
### done
- 对比jira脚本，运行confluence脚本，但是因为对业务以及团队标准不了解，所以无法指导下一步的需求分析

# Day7(26-04-30)
### todo
- [x] 添加字段
- [x] 添加acceptance
- [x] 添加cmt
- [x] 添加图片（注意文件夹结构）
- [x] 添加脚本筛选出p4+story，批量导出

### done
- 今天是有了具体的功能需要实现，所以很专注再ai coding，但是东西没有学到太多，里面涉及到的思路以及技术都是ai帮我相好的，我只是在做一个是否符合业务的判断。可能还需要思考这一部分内容，另外我的token用的太快了，感觉一周就可以把所有的token用完，需要节约一点。

# 3rd Week
# Day8(26-05-06)
### todo
- [x] 表格拉取
- [ ] ~~下划线/划线格式转换~~
- [x] 有序符号的缩进
- [ ] wiley业务线课程学习
- [x] 梳理一下后续的ai自动增量脚本/skill。设计结构-读api文档-写脚本


### done
- 实验阶段拉取脚本提交，学习到的东西：ai-coding、git操作、llm-wiki思想以及实现，但是具体的实现细节我还不知道



# Day9(26-05-07)
### todo & done
- [x] 昨天git犯错，重新拉齐提交
- [x] 回炉学习git

脚本（草稿）：
提交且合并了，三个sheets中phase4

需要保证已有的phase4不变，其他增加。

现在已经把原版三个sheets中的phase4的raw对齐了
需要把三个sheets中除了phase4的未export的issue拉下来
拉下来之前对比diff，然后再提交pr。


# Day10(26-05-08)
### todo
- [x] 自动更新相关接口和参数搞清楚
- [x] 自动更新逻辑搞清楚，写代码
- [x] ai的申请弄好
- [x] clarity的权限弄好

### done
- 把相关的api搞得差不多弄懂了


# Day11(26-05-09)
### todo
- [x] 自动更新代码


# 4th Week
# Day12(26-05-11)
### todo
- [x] 自动增长考虑：新增的story内容如何处理
- [ ] confluence如何抓取
- [ ] 计网学习

### done
- 新增story使用github的action


- [x] 自动更新脚本参数+结构修改


# Day13(26-05-13)
### todo
- [x] 自动更新脚本参数+结构修改
- [x] swagger接口SIMT检验是否case全覆盖

### done
- swagger接口统计任务大致思路有

1. 自动更新脚本(jira-auto-reexport)参数+结构修改，提交到对应的pr
2. api case统计覆盖率
   - 相关调研：intellij中的find usage功能比较复杂，主要是构建索引和检索的策略比较复杂
	- 统计分类思路：只存在于文档/只存在于代码/两者对齐（需文档存在&&代码常量定义&&service实现&&test case中测试有调用）


# Day14(26-05-14)
### todo
- [x] 覆盖统计接口草稿精进
- [x] [vpn初步学习](https://xzcoder.com/posts/network/05-simple-vpn.html)

### done
- 对vpn有了初步了解


# Day15(26-05-15)
### idea
- 关于爬墙xhs的发布：日常训练合集/动作合集/探馆合集。这就要求把所有视频存在一个地方，然后需要做视频时去拿素材。以及需要每提高效率爬墙，不至于再来一次
- 关于赚钱：希望我有更多时间思考如何提高自己的薪资。完成财富积累。kk给的大致时间是10-15年，我想压缩成5年。所以多多摄入商业思维，多多实践商业策略，是长期要做的事情。同时英语也是必须要继续学习的。

### todo
- [x] 覆盖统计接口修改
- [x] 覆盖统计接口java版review
### next work
- [x] 导出swagger结果到csv中（url，method，deprecated）



# 5th Week
# Day16(26-05-18)
### todo
- [x] 读harness的实践

# Day17(26-05-20)
### todo
- [x] 调整java版本的脚本，并且把excel内容统计出来。这次可能需要多多询问了
- [x] 首先还是把这个覆盖率统计清楚（可以让ai暴力枚举
- [x] 然后把excel统计清楚


# Day18(26-05-21)
### todo
- [x] 理清楚新需求
- [x] 开始coding

### motivation
- 想到妈妈给我付房租说希望我学到东西，不能辜负妈妈的期望，所以更加努力学习
- 想到我望着那些很强的爬墙er们，像黑黑原野我就非常想跟上她们的脚步。


# Day19(26-05-22)
### todo
- [x] 先询问标准的设计是怎样的（脚本+文档--help）
- [x] 然后添加一些修改：可选json之类的
- [x] 整理成可用版本，标准化脚本+文档
- [ ] ~~尝试动态方法完成这个统计脚本~~



# 6th Week
# Day20(26-05-25)
### todo
- [x] 把代码简化一下，只剩swagger api和const的对应
- [x] 偷学：初识agent


# Day21(26-05-27)
### todo
- [x] 偷学：agent项目
- [x] 把进度更新一下，然后要新的任务
- [x] jira新的对齐任务
- [x] jira推送knowledge


# Day22(26-05-28)
### todo
- [x] 偷学：agent项目2


# Day23(26-05-29)
### todo
- [x] 偷学：agent项目3+4
- [x] 询问新的任务：服务号如何微信授权登录wiley的官网
- [ ] 想想怎么偷ai的额度

### INFO
- agent项目5需要一些别的知识GRPO什么的，先看后面的几个项目，没问题再一边跑一跑一边学学ai基础知识。


# 7th Week
# Day24(26-06-01)
### todo
- [x] 简易覆盖率代码弄清楚
- [x] 服务号微信授权登录调研
- [x] 偷学：agent项目6

### notice
- 上班太分神，虽然一直在思考自己的事情，但是那是没有实践的，只是想不太够。一定要养成在做什么就在什么，专注当下的能力。

# Day25(26-06-03)
### todo
- [x] 1H:把我的os的计划/复盘模板改进一下
- [x] 1H:偷学：agent项目
- [x] 1H:服务号微信授权登录可行性分析
- [x] 2H:api覆盖，做过滤

### done
- 更新总体os设计文件、新增财务管理系统文件、调整创建周复盘模板、调整日记模板


# Day26(26-06-04)
### todo
- [x] 2H:导出story脚本做修改
- [x] 1H:agent项目代码跑起来
- [x] 1H:学习使用uv代替pip

### done
- 知道了python中的uv包管理器，感觉比pip更好用，不仅仅时快，尤其是对于管理依赖关系和虚拟环境方面。之后可以尝试把之前的项目都迁移到uv上来，看看效果如何。