import base64
from io import BytesIO
import logging
import os
import json
import random
import string
import re
import uuid
from venv import logger
from openai import OpenAI
from dotenv import load_dotenv
import sys
from PIL import Image
import requests
from modules.data_generator import DataGenerator
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from app.Utils.general_utils import print_colored
from app.Services.layouts.opencv_layout_ratherof import generate_ratherof_video
load_dotenv()

api_key_openai = os.getenv("OPENAI_API_KEY")
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
import json
import os

def process_dilemas_for_slides(json_file_path):
    """
    Process dilemas_generados.json to extract intro_text and build slides data
    
    Args:
        json_file_path (str): Path to the dilemas JSON file
        
    Returns:
        tuple: (intro_text, slides_data)
            - intro_text (str): Intro text from the first dilema
            - slides_data (list): List of dictionaries with slide data
    """
    def clean_text(text):
        text = text.replace(',', '')
        # Reemplazar caracteres exclusivos del español
        text = text.translate(str.maketrans("áéíóúÁÉÍÓÚñÑ", "aeiouAEIOUNN"))
        
        # Eliminar signos de puntuación
        text = text.translate(str.maketrans("", "", string.punctuation))
        
        # Eliminar emojis (cualquier caracter en el rango Unicode de emojis)
        text = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F700-\U0001F77F\U0001F780-\U0001F7FF\U0001F800-\U0001F8FF\U0001F900-\U0001F9FF\U0001FA00-\U0001FA6F\U0001FA70-\U0001FAFF\U00002702-\U000027B0]+', '', text)

        return text
    
    # Load JSON data
    with open(json_file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    successful_dilemas = data.get('successful', {})
    
    # Get intro_text from the first element
    first_dilema_key = next(iter(successful_dilemas), None)
    intro_text = ""
    if first_dilema_key:
        intro_text = successful_dilemas[first_dilema_key].get('intro_text', '')
        intro_text = clean_text(intro_text)
    
    # Create slides data
    slides_data = []
    for i, (content_id, dilema) in enumerate(successful_dilemas.items()):
        # Get options from voting prediction
        option_a = dilema['voting_prediction']['option_a']['text']
        option_b = dilema['voting_prediction']['option_b']['text']
        
        # Clean the options text
        option_a = clean_text(option_a)
        option_b = clean_text(option_b)
        
        # Get percentages
        percentage_a = dilema['voting_prediction']['option_a']['percentage']
        percentage_b = dilema['voting_prediction']['option_b']['percentage']
        
        # Format question using example_question template
        question = dilema.get('example_question', '{opcion_a} o {opcion_b}')
        question = question.replace('{opcion_a}', option_a).replace('{opcion_b}', option_b)
        question = clean_text(question)
        
        # Create slide data
        slide_data = {
            'index': i,
            'question': question,
            'options': [option_a, option_b],
            'percentages': [percentage_a, percentage_b]
        }
        
        slides_data.append(slide_data)
    
    return intro_text, slides_data


def print_result(result: dict):
    """Print a single result in a formatted way"""
    print("\n" + "=" * 50)
    print(f"💭 {result['dilemma']}")
    print("\n👥 Opciones:")
    print(f"   A) {result['voting_prediction']['option_a']['text']} "
          f"({result['voting_prediction']['option_a']['percentage']:.1f}%)")
    print(f"   B) {result['voting_prediction']['option_b']['text']} "
          f"({result['voting_prediction']['option_b']['percentage']:.1f}%)")
    print("=" * 50)

def generate_dilemas(data_generator: DataGenerator, 
                    num_dilemas: int = 5,
                    category: str = "sexualidad",
                    template: str = "Amor",
                    output_file: str = None,
                    max_attempts: int = 100) -> None:
    """
    Genera dilemas usando el generador de datos
    
    Args:
        data_generator: Instancia de DataGenerator
        num_dilemas: Número de dilemas exitosos a generar
        category: Categoría específica a usar (opcional)
        template: Template específico a usar (opcional)
        output_file: Archivo donde guardar los resultados (opcional)
        max_attempts: Número máximo de intentos para generar dilemas exitosos
    """
    logger.info(f"Generando {num_dilemas} dilemas...")
    
    # Preparar categorías
    categories = [category] if category else None
    
    # Generar dilemas
    result = data_generator.generate_batch(
        successful_count=num_dilemas,
        categories=categories,
        template=template,
        output_file=output_file,
        max_attempts=max_attempts
    )
    
    # Imprimir resultados
    print("\n=== Dilemas Generados ===")
    for content_id, content in result["successful"].items():
        print(f"\nDilema {content_id}:")
        print(f"Categoría: {content['category']}")
        print(f"Template: {content['template']}")
        print(f"Tono: {content['tone']}")
        print(f"Hook: {content['intro_text']}")
        print(f"Dilema: {content['dilemma']}")
        print(f"Opción A ({content['voting_prediction']['option_a']['percentage']}%): {content['voting_prediction']['option_a']['text']}")
        print(f"Opción B ({content['voting_prediction']['option_b']['percentage']}%): {content['voting_prediction']['option_b']['text']}")
        print("-" * 50)
    
    # Imprimir resumen
    print("\n=== Resumen ===")
    print(f"Dilemas exitosos: {len(result['successful'])}")
    print(f"Intentos fallidos: {len(result['failed'])}")
    print(f"Total de intentos: {result['metadata']['total_attempts']}")
    

from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
client_eleven = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

def text_to_speech_file(voice_folder:str,text: str,index : int) -> str:
    # Convert text to speech
    response = client_eleven.text_to_speech.convert(
        voice_id="onwK4e9ZLuTAKqWW03F9",  
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
            speed=1.0,
        ),
    )

    # Generate unique filename and save
    file_name = f"voice_{index}.mp3"
    file_path= os.path.join(voice_folder, file_name)
    with open(file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print_colored(f"Audio generado perfectamente en {voice_folder} con nombre {text}", 32)
    return voice_folder
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
def generate_image(img_name:str,prompt:str, image_dir:str):
        
        generation_response = client.images.generate(
            model = "dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            response_format="url",
        )
        generated_image_filepath = os.path.join(image_dir, img_name)
        generated_image_url = generation_response.data[0].url
        generated_image = requests.get(generated_image_url).content
        with open(generated_image_filepath, "wb") as image_file:
            image_file.write(generated_image)    

def main():
    try:
        print("🚀 Iniciando generador de dilemas...")
        
        # Load configuration using relative path
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        # Get output path using relative path
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Resources", "RatherThan", "json")
        os.makedirs(output_dir, exist_ok=True)
        output_file =  "app\Services\modules\dilemas_generados.json"
        
        # Initialize generator
        data_generator = DataGenerator(config)
        
        print_colored("Generando dilemas...", 34)
        generate_dilemas(
            data_generator=data_generator,
            num_dilemas=5,
            category=None,
            template=None,
            output_file=output_file
        )
       
        json_path = "app\Services\modules\dilemas_generados.json"
        print_colored("Procesando dilemas para generar slides...", 33)
        intro_text, slides = process_dilemas_for_slides(json_path)
        intro_text = intro_text + "?"+ "Contesta con honestidad"
        image_dir_name  = r"app\Resources\RatherThan\ImagesExample"
        image_dir = os.path.join(os.curdir, image_dir_name)
        voices_folder = "app/Resources/RatherThan/Sounds/voices"
        print(f"Intro Text: {intro_text}")
        print(f"\nSlides:f{slides}")
        #text_to_speech_file(voices_folder,intro_text,0)
        #generate_image("img0.png",intro_text,image_dir)
        pairs = []
        index = 0
        for slide in slides:
            category = slide['question']
            index += 1
            option_a = slide['options'][0]
            pairs.append((f"{image_dir_name}/img{index}.png", option_a, percentage_a))
            option_b = slide['options'][1]
            index += 1
            pairs.append((f"{image_dir_name}/img{index}.png", option_b, percentage_b))
            percentage_a = slide['percentages'][0]
            percentage_b = slide['percentages'][1]
            voice_text= option_a + " o " + option_b + "?"
            # generate_image(f"img{index}.png",option_a,image_dir)
            # generate_image(f"img{index+1}.png",option_b,image_dir)
            # print_colored(f"Imagenes generadas correctamente para slide {slide['index']}...", 33)
            # print(f"\nSlide {slide['index']}:")
            # print(f"voice_text: {voice_text}")
            # print(f"Options: {option_a} ({percentage_a}%) vs {option_b} ({percentage_b}%)")
            # print_colored(f"Generando voces para slide {slide['index']}...", 33)
            # text_to_speech_file(voices_folder,voice_text,index)
            
            
        print_colored(f"\nPairs: {pairs}",34)
        print_colored("Generando video...", 33)
        # intro_image = "app/Resources/RatherThan/ImagesExample/img0.png"
        # generate_ratherof_video(intro_image, intro_text, pairs, voices_folder)
        # print_colored("Video generado correctamente...", 32)

        # intro_image = "app/Resources/RatherThan/ImagesExample/img0.png"
        # intro_text  = "Veamos si eres un genio estrategico o simplemente un cobarde. Contesta con honestidad"
        # pairs = [
        #     ("app/Resources/RatherThan/ImagesExample/img1.png", "Tener acceso a toda la informacion del mundo, pero no poder compartirla con nadie", 72),
        #     ("app/Resources/RatherThan/ImagesExample/img2.png", "Que todos tengan acceso a la informacion menos tu", 28),
        #     ("app/Resources/RatherThan/ImagesExample/img3.png", " Ser la persona mas inteligente del mundo, pero nadie te cree nunca", 80),
        #     ("app/Resources/RatherThan/ImagesExample/img4.png", "Ser promedio, pero que todos piensen que eres un genio", 20),
        #     ("app/Resources/RatherThan/ImagesExample/img5.png", "Tener el control total del mundo por un solo dia", 55),
        #     ("app/Resources/RatherThan/ImagesExample/img6.png", "Tener influencia sobre el mundo por toda tu vida, pero sin que nadie lo note", 45),
        # ]
        # voices_folder = "app/Resources/RatherThan/Sounds/voices"
        # generate_ratherof_video(intro_image, intro_text, pairs, voices_folder)







        
    except Exception as e:
        logging.error(f"Error en el script principal: {str(e)}")
        raise

if __name__ == "__main__":
    main()