from DrissionPage import ChromiumPage, ChromiumOptions

# 初始化配置对象
co = ChromiumOptions()

# 核心设定：指定一个独立的本地文件夹作为该浏览器的用户数据目录
# 这会在你的当前目录下生成一个 'Lit_Bot_Profile' 文件夹
# 它将专门用于累积这个防反爬浏览器的 Cookie 和信誉度
co.set_user_data_path('./Lit_Bot_Profile') 

# 启动具有底层隐蔽特性的浏览器实例
page = ChromiumPage(co)

# 让浏览器直接打开图书馆的登录页或首页 (请替换为实际 URL)
page.get('https://你的图书馆网址.com')

print("浏览器已启动，底层指纹已抹除。现在请接管鼠标进行人工测试...")
# 脚本运行到这里会保持打开状态，你可以开始手动操作了