# 协作状态配置

报告仍由 GitHub Pages 公开展示，Supabase 只保存每个 Issue 的状态和备注。

1. 在 Supabase 创建项目。
2. 在 SQL Editor 执行 `supabase/schema.sql`。
3. 在 Authentication → URL Configuration 中配置：
   - Site URL：`https://xueyinglulu-create.github.io/flash-purchase-store-ui-review/`
   - Redirect URL：同上。
4. 复制 Project URL 与 public anon key，填入 `collaboration-config.js`，并把 `enabled` 改为 `true`。
5. 发布到 GitHub Pages。

权限模型：

- 匿名用户只能读取状态和备注。
- 登录用户可以新增或更新状态和备注。
- 页面不会嵌入 service role key 或 GitHub 写入凭据。
- 编辑失败时保留当前浏览器的未同步草稿。
