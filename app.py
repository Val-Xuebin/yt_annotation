import os, json, subprocess
import streamlit as st
from yt_dlp import YoutubeDL
from datetime import datetime
import ffmpeg
import re

# 键为类别缩写，用于图片命名；值为类别全称，用于类别标注
CATEGORY_MAP = {
    "PF" : 'Personal Foul',
    "FS" : 'False Start'
}
CATEGORIES = list(CATEGORY_MAP.keys())

BASE_DIR = os.getcwd()
VIDEO_DIR = os.path.join(BASE_DIR, "videos")
FRAME_DIR = os.path.join(BASE_DIR, "frames")
META_PATH = os.path.join(BASE_DIR, "meta/data.json")
VIDEO_META_FILE = os.path.join(VIDEO_DIR, "video_meta.json")
ANNOTATION_GUIDE_PATH = os.path.join(BASE_DIR, "meta/annotation_guide.md")
COOKIE_PATH = os.path.join(BASE_DIR, "cookies.txt")  # 放置你刚才导出的 cookie 文件

DEFAULT_GUIDE = """

该标注内容可在该App.py文件的CATEGORY_MAP字典中修改。\n
**Pre-Snap**\n
FS: False Start\n
IS: Illegal Shift\n
IM: Illegal Motion\n
IF: Illegal Formation\n
OF: Offside/Encroachment\n
NI: Neutral Zone Infraction\n
EF: Encroachment\n
DG: Delay of Game\n

**Post-Snap**\n
PI: Pass Interference\n
HF: Holding (Foul)\n
IC: Illegal Contact\n
"""

def load_annotation_guide():
    if not os.path.exists(ANNOTATION_GUIDE_PATH) or os.path.getsize(ANNOTATION_GUIDE_PATH) == 0:
        with open(ANNOTATION_GUIDE_PATH, "w", encoding="utf-8") as f:
            f.write(DEFAULT_GUIDE)
        return DEFAULT_GUIDE
    with open(ANNOTATION_GUIDE_PATH, "r", encoding="utf-8") as f:
        content = f.read().strip()
        return content if content else DEFAULT_GUIDE

def ensure_directories():
    os.makedirs(VIDEO_DIR, exist_ok=True)
    os.makedirs(FRAME_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    for cat in CATEGORIES:
        os.makedirs(os.path.join(FRAME_DIR, cat), exist_ok=True)

def load_tasks():
    if os.path.exists(META_PATH):
        with open(META_PATH, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_tasks(tasks):
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)


def load_metadata():
    if os.path.exists(VIDEO_META_FILE):
        with open(VIDEO_META_FILE, "r") as f:
            metadata = json.load(f)

        # 清理不存在的视频文件对应的元数据
        updated_metadata = {}
        for video_id, data in metadata.items():
            file_path = os.path.join(VIDEO_DIR, data.get("filename", ""))
            if os.path.exists(file_path):
                updated_metadata[video_id] = data
        # 若有改动则保存
        if updated_metadata != metadata:
            with open(VIDEO_META_FILE, "w") as f:
                json.dump(updated_metadata, f, indent=2)

        return updated_metadata
    return {}

def save_metadata(metadata):
    with open(VIDEO_META_FILE, "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
        
def download_video(video_url, progress_bar, status_placeholder):
    video_id = video_url.split("v=")[-1].split("&")[0]
    video_path = os.path.join(VIDEO_DIR, f"{video_id}.mp4")
    if os.path.exists(video_path):
        progress_bar.progress(1.0)
        status_placeholder.write("✅ 视频已存在，跳过下载。")
        return video_path

    try:
        ydl_opts = {"quiet": True, "skip_download": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            title = info.get("title", "unknown_title")

        # 下载视频（用 subprocess 或 yt_dlp 都可）
        command = [
            "yt-dlp",
            "--cookies-from-browser", "chrome",
            "-f", "best",
            "-o", video_path,
            video_url
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        pattern = re.compile(r"\[download\]\s+(\d{1,3}(?:\.\d+)?)%\s+of\s+~?([\d\.]+)([KMG]iB)")
        last_percent = 0.0
        total_size_str = ""

        for line in process.stdout:
            match = pattern.search(line)
            if match:
                percent = float(match.group(1)) / 100
                size = match.group(2)
                unit = match.group(3)
                total_size_str = f"{size}{unit}"
                if percent - last_percent >= 0.005:
                    progress_bar.progress(min(max(percent, 0.0), 1.0))
                    status_placeholder.write(f"⬇ 正在下载：{match.group(1)}% of {total_size_str}")
                    last_percent = percent

        process.wait()
        if process.returncode != 0:
            raise RuntimeError("yt-dlp download failed.")

        # 保存 metadata
        metadata = load_metadata()
        metadata[video_id] = {"title": title, "video_url": video_url ,"filename": f"{video_id}.mp4"}
        save_metadata(metadata)

        progress_bar.progress(1.0)
        status_placeholder.write(f"✅ 下载完成：{title} 共 {total_size_str}")
        return video_path
    except Exception as e:
        status_placeholder.error(f"下载失败: {e}")
        raise

def extract_frame(video_path, timestamp, output_image):
    subprocess.run([
        "ffmpeg", "-ss", timestamp, "-i", video_path,
        "-frames:v", "1", "-q:v", "2", "-y", output_image
    ], check=True)

def get_video_duration(video_path):
    probe = ffmpeg.probe(video_path)
    return float(probe['format']['duration'])

def is_valid_timestamp(timestamp_str, max_seconds):
    try:
        h, m, s = map(int, timestamp_str.strip().split(":"))
        total_sec = h * 3600 + m * 60 + s
        return 0 <= total_sec <= max_seconds
    except:
        return False

def get_next_index(category):
    category_path = os.path.join(FRAME_DIR, category)
    existing = [f for f in os.listdir(category_path) if f.startswith(f"{category}-") and f.endswith(".jpg")]
    numbers = [int(f.split("-")[1].split(".")[0]) for f in existing if "-" in f]
    return max(numbers, default=0) + 1

def render_sidebar(tasks):
    st.sidebar.header("📑 已保存标注")
    col_btn1, col_btn2 = st.sidebar.columns([1, 2])

    if col_btn1.button("🔄 刷新"):
        st.session_state.tasks = load_tasks()

    if col_btn2.button("📤 Export 未上传标注"):
        export_dir = os.path.join(BASE_DIR, "meta/upload")
        os.makedirs(export_dir, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = os.path.join(export_dir, f"export_{timestamp_str}.json")

        export_data = [t.copy() for t in st.session_state.tasks if not t.get("Uploaded", False)]

        if export_data:
            for t in export_data:
                t["Uploaded"] = True
            for t in st.session_state.tasks:
                if not t.get("Uploaded", False):
                    t["Uploaded"] = True
            save_tasks(st.session_state.tasks)

            if not include_explanation:
                for t in export_data:
                    t.pop("explanation", None)

            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            st.sidebar.success(f"✅ 导出成功，共 {len(export_data)} 条，文件: {export_path}")
        else:
            st.sidebar.info("没有需要导出的标注")


    include_explanation = st.sidebar.checkbox("导出时包含说明", value=True)

    # ------------------------- #
    # 展示标注任务（逆序+筛选）  #
    # ------------------------- #

    # 筛选上传状态
    show_only_unuploaded = st.sidebar.checkbox("仅显示未上传标注", value=False)
    tasks_to_display = reversed(st.session_state.tasks)  # 逆序展示（新在上）

    for i_display, task in enumerate(tasks_to_display):
        # 过滤：只显示未上传项
        if show_only_unuploaded and task.get("Uploaded", False):
            continue

        timestamp = task.get("timestamp", "未知时间")
        image_path = task.get("image", "")
        filename = task.get("filename", os.path.basename(image_path.split("?d=")[-1]))
        category = task.get("category", "未知")
        explanation = task.get("explanation", "")
        video_url = task.get("video_url", "")

        i = st.session_state.tasks.index(task)  # 从原始列表中查出真实索引（用于修改/删除）

        expander_title = f"{timestamp} - {filename}"
        with st.sidebar.expander(expander_title):
            image_local_path = os.path.join(BASE_DIR, image_path.split("?d=")[-1]) if image_path else ""
            if os.path.exists(image_local_path):
                st.image(image_local_path, caption=filename, use_container_width=True)
            else:
                st.warning("⚠ 找不到图片文件")

            st.markdown(f"**类别**: {category}")
            st.markdown(f"**说明**: {explanation}")
            st.markdown(f"**视频链接**: {video_url}")
            st.markdown(f"**上传状态**: {'✅ 已上传' if task.get('Uploaded', False) else '❌ 未上传'}")

            col1, col2 = st.columns(2)
            if col1.button("🗑 删除", key=f"delete_{i}"):
                try:
                    image_file_path = os.path.join(FRAME_DIR, category, filename)
                    if os.path.exists(image_file_path):
                        os.remove(image_file_path)
                except Exception as e:
                    st.error(f"删除图片出错: {e}")

                st.session_state.tasks.pop(i)
                save_tasks(st.session_state.tasks)
                st.rerun()

            if col2.button("✏ 修改说明", key=f"edit_{i}"):
                st.session_state.edit_index = i
                st.rerun()

            if "edit_index" in st.session_state and st.session_state.edit_index == i:
                current_explanation = st.session_state.tasks[i].get("explanation", "")
                new_explanation = st.text_area("请输入新的说明：", value=current_explanation, key=f"ex_input_{i}")
                if st.button("✅ 保存修改", key=f"save_edit_{i}"):
                    st.session_state.tasks[i]["explanation"] = new_explanation
                    st.session_state.tasks[i]["Uploaded"] = False  # 修改说明后上传状态设为 False
                    save_tasks(st.session_state.tasks)
                    st.success("说明已更新！")
                    del st.session_state.edit_index
                    st.rerun()


def finalize_save(preview_image_path, video_url, timestamp, category, explanation, tasks):
    # 1. 检查是否存在重复标注
    duplicate_exists = any(t['video_url'] == video_url and t['timestamp'] == timestamp for t in tasks)

    # 2. 如果有重复并且不是强制保存状态，提示用户确认
    if duplicate_exists and not st.session_state.get("force_save", False):
        st.warning("⚠️ 已存在相同视频链接与时间戳的标注。是否继续保存？")
        if st.button("确认继续保存"):
            st.session_state.force_save = True
            st.experimental_rerun()
        return  # 用户尚未确认，终止函数

    # 3. 执行保存流程
    index = get_next_index(category)
    filename = f"{category}-{index}.jpg"
    final_path = os.path.join(FRAME_DIR, category, filename)
    os.rename(preview_image_path, final_path)
    image_url = f"/data/local-files/?d=frames/{category}/{filename}"

    task = {
        "image": image_url,
        "filename": filename,
        "video_url": video_url,
        "timestamp": timestamp,
        "category": CATEGORY_MAP[category],
        "explanation": explanation,
        "Uploaded": False
    }

    tasks.append(task)
    save_tasks(tasks)

    # 4. 重置 session_state 并反馈用户
    st.success(f"已保存: {filename}")
    st.session_state.force_save = False
    st.session_state.tasks = load_tasks()


# ----------- Streamlit UI -----------
st.set_page_config(layout="wide")
st.title("🎬 视频标注工具")

ensure_directories()
if "tasks" not in st.session_state:
    st.session_state.tasks = load_tasks()
if "video_path" not in st.session_state:
    st.session_state.video_path = None
if "video_url" not in st.session_state:
    st.session_state.video_url = ""
if "preview_ready" not in st.session_state:
    st.session_state.preview_ready = False
if "force_save" not in st.session_state:
    st.session_state.force_save = False

render_sidebar(st.session_state.tasks)
# 展示查看的标注信息
if "selected_task" in st.session_state:
    st.markdown("### 🔍 标注详情预览")
    selected = st.session_state.selected_task
    img_path = os.path.join(BASE_DIR, selected['image'].split("?d=")[-1])
    st.image(img_path, caption=f"{selected['category']} - {selected['timestamp']}")
    st.json(selected)

# 编辑标注逻辑
if "editing_task_idx" in st.session_state:
    st.markdown("### 🛠 编辑标注信息")
    edit_data = st.session_state.editing_task_data

    new_category_display = [f"{abbr}：{CATEGORY_MAP[abbr]}" for abbr in CATEGORIES]
    new_category = st.selectbox("修改类别", new_category_display, index=CATEGORIES.index(edit_data["category"]))
    new_explanation = st.text_area("修改说明", value=edit_data["explanation"])
    new_timestamp = st.text_input("修改时间戳 (HH:MM:SS)", value=edit_data["timestamp"])

    if st.button("💾 保存修改"):
        # 修改json数据
        edit_data["category"] = new_category.split("：")[0]
        edit_data["category_full"] = CATEGORY_MAP[edit_data["category"]]
        edit_data["explanation"] = new_explanation
        edit_data["timestamp"] = new_timestamp

        # 更新图片文件名路径（如类别改变则文件名路径也变）
        old_img_path = os.path.join(BASE_DIR, edit_data["image"].split("?d=")[-1])
        new_filename = f"{edit_data['category']}-{get_next_index(edit_data['category'])}.jpg"
        new_img_path = os.path.join(FRAME_DIR, edit_data["category"], new_filename)

        os.makedirs(os.path.dirname(new_img_path), exist_ok=True)
        os.rename(old_img_path, new_img_path)

        edit_data["filename"] = new_filename
        edit_data["image"] = f"/data/local-files/?d=frames/{edit_data['category']}/{new_filename}"

        # 更新任务列表
        st.session_state.tasks[st.session_state.editing_task_idx] = edit_data
        save_tasks(st.session_state.tasks)

        st.success("✅ 修改完成")
        st.session_state.pop("editing_task_idx")
        st.session_state.pop("editing_task_data")
        st.rerun()

st.subheader("🔗 视频链接输入")
st.session_state.video_url = st.text_input("输入 YouTube 视频链接", st.session_state.video_url)

if st.button("加载视频") and st.session_state.video_url:
    with st.spinner("下载中..."):
        progress = st.progress(0.0)
        status_placeholder = st.empty()
        try:
            st.session_state.video_path = download_video(st.session_state.video_url, progress, status_placeholder)
        except Exception as e:
            st.error(f"下载失败: {e}")
        progress.empty()

metadata = load_metadata()

if metadata:
    # 构造下拉选择项：显示 title，内部值为 video_id
    options = {v["title"]: k for k, v in metadata.items()}
    selected_title = st.selectbox("选择一个已下载视频：", list(options.keys()))

    selected_video_id = options[selected_title]
    selected_video_path = os.path.join(VIDEO_DIR, metadata[selected_video_id]["filename"])
    st.session_state.video_url = metadata[selected_video_id]["video_url"]
    if st.button("加载该视频"):
        st.session_state.video_path = selected_video_path
        
if st.session_state.video_path:
    st.video(st.session_state.video_path)
    st.markdown("---")
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("📝 标注区域")
        category_display = [f"{abbr}：{CATEGORY_MAP[abbr]}" for abbr in CATEGORIES]
        category_selection = st.selectbox("选择标签类别", category_display)
        category = category_selection.split("：")[0]

        time_col1, time_col2, time_col3 = st.columns([1, 1, 1])
        hour = time_col1.number_input("小时", min_value=0, max_value=99, step=1, value=0, key="hour")
        minute = time_col2.number_input("分钟", min_value=0, max_value=59, step=1, value=0, key="minute")
        second = time_col3.number_input("秒", min_value=0, max_value=59, step=1, value=0, key="second")

        timestamp_input = f"{int(hour):02}:{int(minute):02}:{int(second):02}"
        explanation = st.text_area("标注说明 explanation")
        col_preview, col_save = st.columns([1, 1])
        preview_trigger = col_preview.button("📸 截图预览")
        confirm_trigger = col_save.button("✅ 确认保存")

    with col2:
        st.markdown("### 🧾 标注提示")
        guide_text = load_annotation_guide()
        with st.container():
            st.markdown(
                f"""
                <div style='max-height: 300px; overflow-y: auto; padding-right:10px;'>
                <pre>{guide_text}</pre>
                </div>
                """,
                unsafe_allow_html=True
            )

    if preview_trigger:
        max_dur = get_video_duration(st.session_state.video_path)
        if is_valid_timestamp(timestamp_input, max_dur):
            temp_preview_path = os.path.join(BASE_DIR, "preview.jpg")
            try:
                extract_frame(st.session_state.video_path, timestamp_input, temp_preview_path)
                st.session_state.preview_ready = True
                st.session_state.preview_info = {
                    "path": temp_preview_path,
                    "timestamp": timestamp_input,
                    "category": category,
                    "explanation": explanation
                }
            except Exception as e:
                st.error(f"截图失败: {e}")
        else:
            st.warning("请输入有效的时间戳（HH:MM:SS）并确保在视频时长范围内。")

    if st.session_state.preview_ready:
        st.image(st.session_state.preview_info["path"], caption="截图预览", use_container_width=True)
        if confirm_trigger:
            preview = st.session_state.preview_info
            finalize_save(
                preview_image_path=preview["path"],
                video_url=st.session_state.video_url,
                timestamp=preview["timestamp"],
                category=preview["category"],
                explanation=preview["explanation"],
                tasks=st.session_state.tasks
            )
            st.session_state.preview_ready = False