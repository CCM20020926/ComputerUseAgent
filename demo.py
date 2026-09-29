from agent.skill_agent import CUASkillAgent

cua_agent = CUASkillAgent(model='gpt-6-luna')


if __name__ == '__main__':
    task = "打开文件管理器，进入我自己的学习目录，新建 cua_test 文件夹。然后进入此文件夹，创建 hello_cua.docx 文件，在此该文件里写一段故事，标题为 Hello CUA，居中、三号字体、加粗；正文小四号字体，首行空 2 格，内容自拟，200字左右。最后双击打开这个 docx 文件。"
    cua_agent.invoke(task)