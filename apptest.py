import streamlit as st
import io
import math
from PIL import Image, ImageDraw, ImageFont
import zipfile

def calculate_panels(height, width, paper_size):
    paper_sizes = {
        'A4': (210, 297),
        'B5': (176, 250),
        'A3': (297, 420),
    }
    
    paper_width, paper_height = paper_sizes[paper_size]
    
    panels_vertical = math.ceil(height / paper_height)
    panels_horizontal = math.ceil(width / paper_width)
    
    total_panels = panels_vertical * panels_horizontal
    
    return total_panels, panels_vertical, panels_horizontal

def split_image(image, height, paper_size):
    paper_sizes = {
        'A4': (2480, 3508),  # A4 at 300 DPI
        'B5': (2079, 2953),  # B5 at 300 DPI
        'A3': (3508, 4961),  # A3 at 300 DPI
    }
    
    paper_width, paper_height = paper_sizes[paper_size]
    
    # フチなし印刷用の余白を追加（300 DPIでの2mmと4mm）
    top_margin = int(2 * 300 / 25.4)  # 2mm in pixels
    left_margin = int(4 * 300 / 25.4)  # 4mm in pixels
    
    aspect_ratio = image.width / image.height
    new_height = int(height * 11.811)  # Convert mm to pixels at 300 DPI
    new_width = int(new_height * aspect_ratio)
    image = image.resize((new_width, new_height), Image.LANCZOS)
    
    panels = []
    for i in range(0, new_height, paper_height):
        for j in range(0, new_width, paper_width):
            panel = Image.new('RGBA', (paper_width, paper_height), (0, 0, 0, 0))  # 透明な背景で初期化
            crop = image.crop((
                max(0, j - left_margin), 
                max(0, i - top_margin), 
                min(j + paper_width - left_margin, new_width), 
                min(i + paper_height - top_margin, new_height)
            ))
            
            # 透明度を保持
            if crop.mode != 'RGBA':
                crop = crop.convert('RGBA')
            
            panel.paste(crop, (left_margin, top_margin), crop)
            panels.append(panel)
    
    return panels


def create_layout_preview(panels_vertical, panels_horizontal, paper_size):
    paper_sizes = {
        'A4': (210, 297),
        'B5': (176, 250),
        'A3': (297, 420),
    }
    paper_width, paper_height = paper_sizes[paper_size]
    
    # プレビューのサイズを設定（大きすぎないように調整）
    scale = min(800 / (paper_width * panels_horizontal), 800 / (paper_height * panels_vertical))
    preview_width = int(paper_width * panels_horizontal * scale)
    preview_height = int(paper_height * panels_vertical * scale)
    
    preview = Image.new('RGB', (preview_width, preview_height), color='white')
    draw = ImageDraw.Draw(preview)
    
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    for i in range(panels_vertical):
        for j in range(panels_horizontal):
            x1 = j * paper_width * scale
            y1 = i * paper_height * scale
            x2 = (j + 1) * paper_width * scale
            y2 = (i + 1) * paper_height * scale
            
            # パネルの枠を描画
            draw.rectangle([x1, y1, x2, y2], outline='black')
            
            # パネル番号を描画
            panel_number = i * panels_horizontal + j + 1
            text = str(panel_number)
            # textbboxを使用してテキストのサイズを取得
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            text_x = int((x1 + x2 - text_width) // 2)
            text_y = int((y1 + y2 - text_height) // 2)
            draw.text((text_x, text_y), text, fill='black', font=font)

    return preview

# Streamlitアプリのメイン部分
st.set_page_config(page_title="アニ研")

st.title('等身ハイスクールver1.5 (フチなし対応)')

height = st.number_input('身長（cm）を入力してください', min_value=100, max_value=250, value=170)
paper_size = st.selectbox('紙のサイズを選択してください', ('A4', 'B5', 'A3'))

uploaded_file = st.file_uploader("写真をアップロードしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    image_height = height * 10  # mmに変換
    image_width = int(image_height * (image.width / image.height))
    
    total_panels, panels_vertical, panels_horizontal = calculate_panels(image_height, image_width, paper_size)
    
    st.write(f'必要な紙の枚数: {total_panels}枚')
    st.write(f'縦: {panels_vertical}枚, 横: {panels_horizontal}枚')
    
    layout_preview = create_layout_preview(panels_vertical, panels_horizontal, paper_size)
    st.subheader("パネルレイアウトプレビュー")
    st.image(layout_preview, caption="(白いところも含まれてます)", use_column_width=True)
    
    panels = split_image(image, image_height, paper_size)
    
    # ZIPファイルを作成
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for i, panel in enumerate(panels):
            st.subheader(f'パネル {i+1}')
            st.image(panel, use_column_width=True)
            
            buf = io.BytesIO()
            panel.save(buf, format='PNG')
            st.download_button(
                label=f"パネル {i+1} をダウンロード",
                data=buf.getvalue(),
                file_name=f"panel_{i+1}.png",
                mime="image/png"
            )
            
            img_byte_arr = io.BytesIO()
            panel.save(img_byte_arr, format='PNG')
            zip_file.writestr(f"panel_{i+1}.png", img_byte_arr.getvalue())
    
    st.download_button(
        label="すべてのパネルをZIPでダウンロード",
        data=zip_buffer.getvalue(),
        file_name="all_panels.zip",
        mime="application/zip"
    )