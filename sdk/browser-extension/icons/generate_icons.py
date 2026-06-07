"""
生成浏览器插件PNG图标
从SVG转换为16/48/128像素的PNG图标
"""
import os

try:
    from PIL import Image
    import cairosvg
except ImportError:
    # 如果没有安装，使用纯Pillow方式生成简单图标
    from PIL import Image, ImageDraw
    
    def create_icon(size):
        """创建简单的盾牌图标"""
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 背景
        padding = size // 8
        draw.rounded_rectangle(
            [padding, padding, size - padding, size - padding],
            radius=size // 8,
            fill=(10, 10, 15, 255)
        )
        
        # 盾牌外框
        shield_padding = size // 4
        draw.rounded_rectangle(
            [shield_padding, shield_padding + size//8, 
             size - shield_padding, size - shield_padding],
            radius=size // 16,
            outline=(60, 252, 140, 255),
            width=max(1, size // 32)
        )
        
        # 中心圆点
        center = size // 2
        radius = size // 16
        draw.ellipse(
            [center - radius, center - radius, 
             center + radius, center + radius],
            fill=(60, 252, 140, 255)
        )
        
        # 底部横条
        bar_width = size // 4
        bar_height = size // 20
        draw.rounded_rectangle(
            [center - bar_width//2, size - shield_padding - bar_height,
             center + bar_width//2, size - shield_padding],
            radius=bar_height // 2,
            fill=(167, 139, 250, 255)
        )
        
        return img
    
    sizes = [16, 48, 128]
    output_dir = os.path.dirname(__file__)
    
    for size in sizes:
        img = create_icon(size)
        output_path = os.path.join(output_dir, f'icon{size}.png')
        img.save(output_path, 'PNG')
        print(f'Created: {output_path}')
    
    print('All icons generated successfully!')