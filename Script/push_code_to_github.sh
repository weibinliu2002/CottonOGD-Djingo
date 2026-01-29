#!/bin/bash

# 切换到项目根目录
cd "$(dirname "$(dirname "$0")")"

# 添加所有更改
git add .

# 提交更改，使用当前日期时间作为提交信息
COMMIT_MSG="Auto commit on $(date '+%Y-%m-%d %H:%M:%S')"
git commit -m "$COMMIT_MSG"

# 推送到GitHub
git push origin development

# 输出执行结果
echo "Auto commit completed at $(date '+%Y-%m-%d %H:%M:%S')"

# 注意：要设置定时执行，请按照以下步骤操作：
# 1. 在Windows上打开"任务计划程序"
# 2. 创建新任务，设置触发时间为每天10:00和12:30
# 3. 操作设置为运行此脚本，使用Git Bash作为执行程序
# 4. 程序/脚本：C:\Program Files\Git\bin\bash.exe
# 5. 添加参数：-c "'D:\science\OGD\Script\push_code_to_github.sh'"
# 6. 确保任务运行时的用户权限有足够的权限访问Git仓库