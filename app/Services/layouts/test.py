from PIL import Image, ImageDraw, ImageFont
import numpy as np
import cv2

def draw_text_with_pil(img_cv2, text, x, y, font_path, font_size=40, color=(255,255,255)):
    # 1. Convertimos la imagen de OpenCV (BGR) a PIL (RGB)
    img_rgb = cv2.cvtColor(img_cv2, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img_rgb)
    
    # 2. Creamos un objeto de dibujo en PIL
    draw = ImageDraw.Draw(pil_img)
    
    # 3. Cargamos la fuente TTF
    font = ImageFont.truetype(font_path, font_size)
    
    # 4. Dibujamos el texto
    # color en PIL es (R,G,B), no necesita alpha
    draw.text((x, y), text, font=font, fill=color)
    
    # 5. Convertimos de vuelta a formato OpenCV (BGR)
    img_cv2_out = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return img_cv2_out

if __name__ == "__main__":
    # Creamos un lienzo vacío en OpenCV
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    # Ruta a tu fuente TTF
    impact_ttf = r"app\Services\fonts\Helvetica\Helvetica-BoldOblique.ttf"
    
    # Dibujamos el texto con Pillow
    img = draw_text_with_pil(img, "Hola con Impact TTF", 50, 100, impact_ttf, font_size=60, color=(0,255,0))
    
    # Mostramos la imagen final con OpenCV
    cv2.imshow("Imagen con TTF (PIL)", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
