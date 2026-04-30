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
- [ ] llm-wiki调研
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
- [ ] 读llm-wiki应用在wiley知识库的设计文档
- [x] 阅读脚本文件内容
- [x] 调整一下原脚本的代码，以及再梳理一下需求重构代码
- [ ] token数量有限制，意味着需要学习一下如何省着用
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