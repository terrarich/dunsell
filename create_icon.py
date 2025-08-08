from PIL import Image
import os

def create_ico_from_image(image_path, output_path="icon.ico", sizes=[16, 32, 48, 64, 128, 256]):
    """
    Конвертирует изображение в .ico файл с несколькими размерами
    """
    try:
        # Открываем изображение
        img = Image.open(image_path)
        
        # Создаем список изображений разных размеров
        icons = []
        for size in sizes:
            resized_img = img.resize((size, size), Image.LANCZOS)
            icons.append(resized_img)
        
        # Сохраняем как .ico
        icons[0].save(output_path, format='ICO', sizes=[(size, size) for size in sizes])
        print(f"Иконка создана: {output_path}")
        
    except Exception as e:
        print(f"Ошибка: {e}")

def create_simple_icon():
    """
    Создает простую иконку для DunSell (если нет изображения)
    """
    # Создаем простое изображение 256x256
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    
    # Рисуем простой символ (например, букву D)
    from PIL import ImageDraw, ImageFont
    
    draw = ImageDraw.Draw(img)
    
    # Фон
    draw.ellipse([20, 20, size-20, size-20], fill=(58, 166, 255, 255))
    
    # Буква D
    try:
        # Пытаемся использовать системный шрифт
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        # Если не получилось, используем стандартный
        font = ImageFont.load_default()
    
    draw.text((size//2-30, size//2-60), "D", fill=(255, 255, 255, 255), font=font)
    
    # Сохраняем как .ico
    icons = []
    sizes = [16, 32, 48, 64, 128, 256]
    for s in sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        icons.append(resized)
    
    icons[0].save("dunsell_icon.ico", format='ICO', sizes=[(s, s) for s in sizes])
    print("Создана простая иконка: dunsell_icon.ico")

if __name__ == "__main__":
    # Если есть изображение, конвертируем его
    if os.path.exists("icon.png"):
        create_ico_from_image("icon.png", "dunsell_icon.ico")
    elif os.path.exists("icon.jpg"):
        create_ico_from_image("icon.jpg", "dunsell_icon.ico")
    else:
        # Создаем простую иконку
        create_simple_icon()
