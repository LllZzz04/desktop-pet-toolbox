from pathlib import Path
import argparse, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FPS = 20
RAW = ROOT / 'preview/raw_final_showcase'
PREVIEW = ROOT / 'preview'
parser = argparse.ArgumentParser()
parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
args = parser.parse_args()

def font(size):
    return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', size)

def frame(t):
    index = max(0, min(887, round(t * FPS) - 1))
    return Image.open(RAW / f'frame_{index:04d}.png').convert('RGB')

def pet_view(im):
    return im.crop((330, 0, 960, 800))

samples = [
    ('普通待机', .3), ('左右看看', 3.25), ('困倦哈欠', 7.6), ('注意鼠标', 11.6),
    ('单击疑问', 13.95), ('三击不满', 15.5), ('护头 · 嘟嘴', 17.7), ('护胸 · 脸红', 20.1),
    ('浅蹲护腿 · 脸红', 22.5), ('拖拽悬挂', 26.7), ('落地缓冲', 29.15), ('持板工作', 32.0),
    ('成功庆祝', 34.85), ('错误反馈', 39.2), ('恢复待机', 42.5), ('统一预览入口', 41.0)
]
tile_w, tile_h, gap = 280, 408, 12
gallery = Image.new('RGB', (4*tile_w+5*gap, 4*tile_h+5*gap+96), (235,237,244))
draw = ImageDraw.Draw(gallery)
draw.text((24,18), 'LUNA · 最终版动画总览', font=font(32), fill=(45,40,52))
draw.text((24,61), '已确认 Phase4.17 · 动作与素材冻结 · 实际 Godot 运行画面', font=font(17), fill=(103,93,112))
for i, (label, t) in enumerate(samples):
    x = gap + (i % 4)*(tile_w+gap)
    y = 96 + gap + (i // 4)*(tile_h+gap)
    im = frame(t)
    if i == 15:
        image = im.resize((tile_w, round(tile_w*800/960)), Image.Resampling.LANCZOS)
        gallery.paste(image, (x, y+85))
    else:
        image = pet_view(im).resize((tile_w, round(tile_w*800/630)), Image.Resampling.LANCZOS)
        gallery.paste(image, (x, y+42))
    draw.text((x+10,y+8), label, font=font(20), fill=(50,43,57))
gallery.save(PREVIEW / 'Luna_Final_Animations.png')

def gif(name, start, end):
    images = []
    for i in range(round(start*FPS), round(end*FPS)):
        im = Image.open(RAW / f'frame_{i:04d}.png').convert('RGB')
        images.append(pet_view(im).resize((378,480), Image.Resampling.LANCZOS))
    # Shared palette prevents changing palette colours from causing flicker.
    sheet = Image.new('RGB', (378*4,480*4))
    for k in range(16):
        sheet.paste(images[min(len(images)-1, k*len(images)//16)], ((k%4)*378,(k//4)*480))
    palette = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    indexed = [im.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG) for im in images]
    indexed[0].save(PREVIEW/name, save_all=True, append_images=indexed[1:], duration=50, loop=0, optimize=False, disposal=2)
    return {'file':name, 'fps':FPS, 'frames':len(images), 'start_seconds':start, 'end_seconds':end, 'size':[378,480]}

clips = [gif('idle_variants.gif', 1.0, 9.8), gif('attention.gif', 10.5,13.1),
         gif('click_feedback.gif',13.5,16.15), gif('drag_and_land.gif',25.5,30.3),
         gif('working.gif',30.4,34.4), gif('success_error.gif',34.4,40.0)]
frame(32.0).save(PREVIEW / 'Luna_Final_Poster.png')
mp4 = None
if args.ffmpeg:
    mp4 = PREVIEW / 'Luna_Final_Showcase.mp4'
    subprocess.run([args.ffmpeg,'-hide_banner','-loglevel','error','-y',
                    '-framerate',str(FPS),'-start_number','0','-i',str(RAW/'frame_%04d.png'),
                    '-frames:v','888','-c:v','libx264','-preset','medium','-crf','18',
                    '-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True)
report = {'pass':True, 'source':'Actual final Godot unified test scene',
          'showcase': {'file':mp4.name if mp4 else None,'fps':20,'duration':44.4,'frames':888,'size':[960,800]},
          'gallery':'Luna_Final_Animations.png', 'clips':clips,
          'retained_approved_previews':['success_v2.gif','success_v2.mp4','success_keyposes.png',
                                       'angry_click_head.gif','angry_click_chest.gif','angry_legs_crouch.gif']}
(ROOT/'data/preview_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'gallery':str(PREVIEW/'Luna_Final_Animations.png'), 'mp4':str(mp4), 'clips':len(clips)},ensure_ascii=False))
