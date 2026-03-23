import streamlit as st
import io
import math
from PIL import Image, ImageDraw, ImageFont
import zipfile

def calculate_panels(height, width, paper_size):
    """height/widthはmm。B5選択時はプリンタ余白を考慮した有効印字領域で枚数を計算。"""
    paper_sizes_mm = {
        'A4': (210, 297),
        'B5': (176, 250),
        'A3': (297, 420),
    }

    paper_width_mm, paper_height_mm = paper_sizes_mm[paper_size]

    # B5時の余白(cm) -> mm
    if paper_size == 'B5':
        left_cm, top_cm, right_cm, bottom_cm = 0.96, 0.84, 0.96, 1.43
        left_mm, top_mm, right_mm, bottom_mm = (
            left_cm * 10,
            top_cm * 10,
            right_cm * 10,
            bottom_cm * 10,
        )
        eff_width_mm = max(1, paper_width_mm - (left_mm + right_mm))
        eff_height_mm = max(1, paper_height_mm - (top_mm + bottom_mm))
    else:
        eff_width_mm, eff_height_mm = paper_width_mm, paper_height_mm

    panels_vertical = math.ceil(height / eff_height_mm)
    panels_horizontal = math.ceil(width / eff_width_mm)

    total_panels = panels_vertical * panels_horizontal

    return total_panels, panels_vertical, panels_horizontal

def split_image(image, height, paper_size):
    """画像を300DPI相当でリサイズし、用紙ごとに分割。
    B5時はプリンタ余白を考慮した有効印字領域ピクセルで分割・出力する（出力画像に余白は含めない）。
    """
    # 用紙サイズ（px, 300DPI想定）
    paper_sizes_px = {
        'A4': (2480, 3508),  # A4 at 300 DPI
        'B5': (2079, 2953),  # B5 at 300 DPI
        'A3': (3508, 4961),  # A3 at 300 DPI
    }

    paper_width_px, paper_height_px = paper_sizes_px[paper_size]

    # mm -> px 変換（300DPI）
    MM_TO_PX = 11.811  # 300 / 25.4

    # 入力画像を指定身長(mm)に合わせてリサイズ
    aspect_ratio = image.width / image.height
    new_height_px = int(height * MM_TO_PX)
    new_width_px = int(new_height_px * aspect_ratio)
    image = image.resize((new_width_px, new_height_px), Image.LANCZOS)

    # 分割ステップ（有効印字領域）と出力パネルサイズの決定
    if paper_size == 'B5':
        # 余白(cm)
        left_cm, top_cm, right_cm, bottom_cm = 0, 0.84, 2.4, 1.8
        # 余白(mm)
        left_mm, top_mm, right_mm, bottom_mm = (
            left_cm * 10,
            top_cm * 10,
            right_cm * 10,
            bottom_cm * 10,
        )
        # 有効印字領域（px）: 用紙px - 余白px
        eff_width_px = max(1, int(round((176 - (left_mm + right_mm)) * MM_TO_PX)))
        eff_height_px = max(1, int(round((250 - (top_mm + bottom_mm)) * MM_TO_PX)))

        step_w, step_h = eff_width_px, eff_height_px
        out_w, out_h = eff_width_px, eff_height_px  # 出力画像に余白を含めない
    else:
        step_w, step_h = paper_width_px, paper_height_px
        out_w, out_h = paper_width_px, paper_height_px

    panels = []
    for i in range(0, new_height_px, step_h):
        for j in range(0, new_width_px, step_w):
            # 出力は白背景のRGB
            panel = Image.new('RGB', (out_w, out_h), (255, 255, 255))
            crop = image.crop((
                j,
                i,
                min(j + step_w, new_width_px),
                min(i + step_h, new_height_px)
            ))

            # 透過付きなら白背景にアルファ合成
            if crop.mode in ("RGBA", "LA") or (crop.mode == "P" and 'transparency' in crop.info):
                # RGBAに変換してマスクを抽出
                rgba = crop.convert("RGBA")
                alpha = rgba.split()[-1]
                # 白背景に合成
                panel.paste(rgba, (0, 0), mask=alpha)
            else:
                panel.paste(crop, (0, 0))
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

st.title('等身ハイスクールver3.1')

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
    
    # レイアウトプレビューを作成して表示
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
            
            # 個別のパネルダウンロードボタン
            buf = io.BytesIO()
            panel.save(buf, format='PNG')
            st.download_button(
                label=f"パネル {i+1} をダウンロード",
                data=buf.getvalue(),
                file_name=f"panel_{i+1}.png",
                mime="image/png"
            )
            
            # ZIPファイルにパネルを追加
            img_byte_arr = io.BytesIO()
            panel.save(img_byte_arr, format='PNG')
            zip_file.writestr(f"panel_{i+1}.png", img_byte_arr.getvalue())
    
    # すべてのパネルをまとめてダウンロードするボタン
    st.download_button(
        label="すべてのパネルをZIPでダウンロード",
        data=zip_buffer.getvalue(),
        file_name="all_panels.zip",
        mime="application/zip"
    )
