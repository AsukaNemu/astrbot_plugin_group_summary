# Changelog

## v0.1.5

- 新增 `.version` 命令，输出当前插件版本号

## v0.1.4

- 总结转发覆盖所有情况：成功、失败、信息不足均私聊发送给管理员

## v0.1.2

- 新增 admin_qq 配置项，总结成功时私聊转发一份给管理员

## v0.1.0

- 初版发布
- 群聊消息缓存，过滤低信息量消息（"哈哈"、"6"、"？"等）
- 触发词总结（总结、省流、刚刚聊啥等）
- `/总结` 命令总结
- 可配置项：max_messages、trigger_words、ignore_short_message
- 调用 AstrBot LLM provider 生成总结
