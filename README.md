# 📘 Video Annotation Tool

本项目是一个使用 Streamlit 构建的视频事件截图标注工具，支持标注 YouTube 视频中出现的美式橄榄球犯规行为，并保存为结构化数据。

---

## 🔧 功能特性

- 📥 支持从 YouTube 下载视频（需 Chrome cookie）
- 📸 根据用户设定的时间点自动截图
- 🏷 支持 10+ 类别的标签选择
- 📝 每张截图支持文字说明
- 📂 自动分类保存图片
- ✅ 可视化查看、删除已保存标注
- ⬇️ 导出未上传的标注信息（上传状态跟踪）

---

## 🖥 项目运行方法

1. 安装依赖：

```bash
pip install -r requirements.txt
```

2. 确保系统中安装 `ffmpeg` 并配置环境变量：

- Windows: [FFmpeg 下载](https://ffmpeg.org/download.html)
- macOS: `brew install ffmpeg`

3. 运行应用：

```bash
streamlit run app.py
```

---

## 📂 项目结构

```
your_project/
├── app.py                    # 主应用
├── requirements.txt          # Python 依赖
├── README.md                 # 使用说明
├── meta/
│   ├── data.json             # 标注数据（自动生成）
│   └── annotation_guide.md   # 标签指南
├── frames/                   # 保存截图
├── videos/                   # 视频缓存
├── cookies.txt               # YouTube cookie 文件
├── upload/                   # 导出 JSON 标注
```

---

## 🍪 cookies.txt 使用方法

使用浏览器插件导出 `cookies.txt`（登录 YouTube 后），放在项目根目录以支持私有或会员视频下载。

推荐插件：

- [Get cookies.txt Extension (Chrome)](https://chrome.google.com/webstore/detail/get-cookiestxt/)

---

## 🔖 默认标签（犯规行为）

- FS: False Start
- IS: Illegal Shift
- IM: Illegal Motion
- IF: Illegal Formation
- OF: Offside
- NI: Neutral Zone Infraction
- EF: Encroachment
- DG: Delay of Game
- PI: Pass Interference
- HF: Holding (Foul)
- IC: Illegal Contact

---

## 📤 标注导出说明

- 标注记录包含字段 `uploaded: false`
- 点击“📤 Export”后，未上传标注会保存为 JSON 文件，位于 `upload/` 目录
- 命名格式为 `upload_YYYYMMDD_HHMMSS.json`

---

## 👨‍💻 贡献

欢迎通过 issue/PR 提交反馈或优化建议。