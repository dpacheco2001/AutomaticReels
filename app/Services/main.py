import logging
import os
import json
import random
from venv import logger
from modules.data_generator import DataGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
                    category: str = None,
                    template: str = None,
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
        output_file = os.path.join(output_dir, "dilemas_generados.json")
        
        # Initialize generator
        data_generator = DataGenerator(config)
        
        # Generate dilemas with relative output path
        generate_dilemas(
            data_generator=data_generator,
            num_dilemas=5,
            category=None,
            template=None,
            output_file=output_file
        )
        
    except Exception as e:
        logging.error(f"Error en el script principal: {str(e)}")
        raise

if __name__ == "__main__":
    main()