import yaml
import random
import openai
import os
import sys
from typing import Dict, List, Optional, Union
from dotenv import load_dotenv
import logging
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from app.Utils.general_utils import print_colored
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

# Load environment variables
load_dotenv()

class DataGenerator:
    def __init__(self, config: Dict):
        self.config = config
        
        logger.info("Inicializando DataGenerator...")
        
        # Load environment variables from relative path
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        load_dotenv(env_path)
        
        # Get niches from config
        self.niches_data = config.get('niches', {})
        if isinstance(self.niches_data, list):
            self.niches_data = {niche: {} for niche in self.niches_data}
        self.niches = list(self.niches_data.keys())
        logger.info(f"Niches cargados: {self.niches}")
        
        # Get templates and their categories
        self.templates = config.get('templates', {})
        if isinstance(self.templates, list):
            self.templates = {template: {} for template in self.templates}
        self.template_categories = list(self.templates.keys())
        logger.info(f"Templates cargados: {self.template_categories}")
        
        # Get all available categories (for reference)
        self.all_categories = config.get('category', {})
        if isinstance(self.all_categories, list):
            self.all_categories = {cat: cat for cat in self.all_categories}
        logger.info(f"Categorías cargadas: {list(self.all_categories.keys())}")
        
        # Get emoji styles from config
        self.emoji_styles = config.get('emoji_styles', {"default": ["🤔", "💭", "🎯"]})
        if isinstance(self.emoji_styles, list):
            self.emoji_styles = {"default": self.emoji_styles}
        logger.info(f"Emoji styles cargados: {list(self.emoji_styles.keys())}")
        
        # Configure OpenAI from environment variables
        self.openai_config = {
            'model': os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            'temperature': float(os.getenv('OPENAI_TEMPERATURE', '0.8')),
            'max_tokens': int(os.getenv('OPENAI_MAX_TOKENS', '150'))
        }
        
        self.quality_thresholds = config.get('quality_thresholds', {
            'min_quality': 0.8,
            'min_engagement': 0.8,
            'min_coherence': 0.8
        })
        
        self.previous_dilemmas = []
        
        # Configure OpenAI
        self.client = openai.OpenAI()
        
        # Add new attributes for batch tracking
        self.generated_content = {}
        self.failed_content = {}

    def _get_random_template(self, category: str = None) -> str:
        """Get a random template and its category"""
        if category is None:
            category = random.choice(self.template_categories)
        
        # Get questions from template data safely
        template_data = self.templates.get(category, {})
        if isinstance(template_data, list):
            template_data = {"preguntas": template_data}
        
        questions = template_data.get('preguntas', [])
        if isinstance(questions, str):
            questions = [questions]
        elif not isinstance(questions, list):
            questions = []
            
        if not questions:
            return "¿{opcion_a} o {opcion_b}?"
        
        return random.choice(questions)
    
    def _add_random_emoji(self, text: str, category: str) -> str:
        return text

    def _clean_text(self, text: str) -> str:
        """Limpia el texto de caracteres no deseados"""
        return text.replace('****', '').replace('- ', '').replace('¿', '').replace('!', '').strip()

    def _generate_hook(self, category: str, template: str, tone: str) -> str:
        """Genera un hook poderoso basado en el contexto"""
        
        hook_prompt = f"""
        Como experto en psicología social y viral marketing de TikTok, crea UN GANCHO INICIAL EXPLOSIVO que haga IMPOSIBLE no ver el dilema.

        OBJETIVO: Crear una frase que:
        1.  GOLPEE EMOCIONALMENTE en el primer segundo
        2.  Active el sesgo de curiosidad
        3.  Cree tensión psicológica inmediata
        4.  Genere FOMO (miedo a perderse algo)
        5.  Dispare dopamina con anticipación
        6.  Genere un debate interesante
        

        CONTEXTO ESPECÍFICO:
        • Tema: {category}
        • Estilo: {template}
        • Tono: {tone}

        TÉCNICAS PSICOLÓGICAS A USAR :
        • Disonancia cognitiva ("Crees ser X, pero esta pregunta revelará la verdad")
        • Sesgo de autoridad ("El 97% falla esta prueba de personalidad")
        • Prueba social ("Solo 2 de cada 10 eligen correctamente")
        • Pérdida potencial ("Tu respuesta podría costarte todo")
        • Desafío al ego ("Demuestra que no eres como los demás")
        • Misterio intrigante ("La segunda opción esconde un secreto que pocos ven")

        ESTRUCTURA PODEROSA:
        • Máximo 12 palabras
        • Debe crear conflicto interno
        • Tono desafiante/misterioso
        • Dirigido a "tú" directamente
        • Prometer revelación/descubrimiento
        • NO usar emojis (se añaden después)

        EJEMPLOS DE ESTRUCTURA VIRAL:
        MAL: "¿Qué elegirías en esta situación?"
        CORRECTO: "Tu respuesta expondrá tu verdadera personalidad ante todos"
        CORRECTO: "El 98% falla esta prueba de valores morales"
        CORRECTO: "Solo los valientes se atreven a elegir la segunda opción"
        CORRECTO: "Esta decisión revelará tu mayor secreto"

        GENERA UN SOLO HOOK EXPLOSIVO QUE HAGA IMPOSIBLE NO VER EL DILEMA:
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config['model'],
                messages=[{"role": "user", "content": hook_prompt}],
                temperature=0.9,
                max_tokens=50
            )
            
            hook = response.choices[0].message.content.strip()
            hook = self._clean_text(hook)
            if not hook.endswith(('.', '!')):
                hook += '.'
            
            return hook
            
        except Exception as e:
            logger.error(f"Error generating hook: {str(e)}")
            return "Tu respuesta revelará mucho sobre ti."

    def generate_ai_content(self, niche: str, category: str, template: str = None) -> Dict:
        """Generate content using AI with dynamic templates and instructions"""
        logger.info(f"Generando contenido para niche: {niche}, category: {category}, template: {template}")
        
        # Validar que la categoría exista en el config
        if category not in self.all_categories:
            raise ValueError(f"Category {category} not found in config. Available categories: {', '.join(self.all_categories.keys())}")
        if niche not in self.niches_data:
            raise ValueError(f"Niche {niche} not found in niches")
        if template and template not in self.templates:
            raise ValueError(f"Template {template} not found in templates")

        # Si no se especifica template, elegir uno aleatorio
        if not template:
            template_names = list(self.templates.keys())
            if not template_names:
                raise ValueError("No hay templates disponibles en el config")
            template = random.choice(template_names)
        
        logger.info(f"Template seleccionado: {template}")
        
        # Get template data safely
        template_data = self.templates.get(template, {})
        if isinstance(template_data, list):
            template_data = {"preguntas": template_data, "tone": ["casual", "divertido"]}
        
        # Get tone from template and ensure it's a single string
        template_tones = template_data.get('tone', [])
        if isinstance(template_tones, str):
            tone = template_tones
        elif isinstance(template_tones, list) and template_tones:
            tone = random.choice(template_tones)
        else:
            tone = "casual"  # default tone si no hay ninguno
        
        logger.info(f"Tono seleccionado: {tone}")
        
        # Get example questions
        example_questions = template_data.get('preguntas', [])
        if isinstance(example_questions, str):
            example_questions = [example_questions]
        elif not isinstance(example_questions, list):
            example_questions = []
        
        example_questions_str = "\n".join([f"- {q}" for q in example_questions]) if example_questions else ""
        example_questions_str = random.choice(example_questions) if example_questions else ""
        logger.info(f"Example questions: {example_questions_str}")
        # Get category description safely
        category_desc = self.all_categories.get(category, category)
        if isinstance(category_desc, (list, dict)):
            category_desc = str(category_desc)
        
        # Generar el hook después de tener template y tono
        hook = self._generate_hook(category, template, tone)
        logger.info(f"Hook generado: {hook}")

        # Build simpler, more focused prompt
        content_prompt = f"""
        ## Prompt Mejorado para Generar Dilemas Interesantes y Personales

        Genera un dilema corto, relatable y cargado de emoción que enganche a la gente para votar y comentar. Hazlo personal, con un toque de tensión o intriga, y evita que se sienta genérico o predecible.

        ### Contexto: 
        - **Tipo:** {category}  
        - **Template:** {template_data.get('description')}  
        - **Descripción:** {template_data.get('instructions')}
        - **Tono:** {tone}
        ## Instrucciones:
        - **Contexto:** Todo el  dilema debe estar en el contexto de {category} ya que todo el dilema debe estar relacionado con la categoria, pero la pregunta en especifico debe ser de la forma {template_data.get('description')}
        - **Pregunta:** La pregunta debe ser una pregunta que debe estar relacionado con {example_questions_str}, no lo copies, pero usalo de referencia para generar un dilema interesante, ademas es imporantisimo considerar en la generacion del dilema esto {template_data.get('instructions')}
        - **Tono:** Al momento de generar el dilema, ten en ceunta usar el tono {tone}, pero siempre tiene que atrapar al usario
        - Escribe un texto sin usar caracteres exclusivos del español (á, é, í, ó, ú, ñ). No uses emojis ni símbolos especiales
        - Tu salida solo debe tener las opciones, no le información adicional, debe ser : A o B
        - No uses emojis, solo texto
        - IMPORTANTE: Tamaño solo una linea, no mas de 50 caracteres
        - IMPORTANTE: Cantidad de palabras: 10 palabras
        ### Reglas Clave:
        1. **Conexión emocional:** El dilema debe ser una situación personal que el usuario pueda imaginar viviendo. Usa "tú" o "tu" para hacerlo directo.  
        2. **Opciones interesantes:** Evita respuestas obvias; ambas opciones deben ser atractivas pero distintas en enfoque o resultado.  
        3. **Lenguaje juvenil:** Usa un tono casual, coloquial y emojis (según el tono y el estilo del JSON).  
        4. **Toque narrativo:** Incluye un mini-contexto o gancho que despierte curiosidad o debate (sin alargarte).  
        5. **Equilibrio:** Las opciones deben ser cortas, claras y equilibradas en atractivo.  
        6. **Nada de marcas:** No menciones nombres específicos.  
        7. **Invita a participar:** Siempre termina pidiéndole al usuario que vote y comente.  
        8. **Único y creativo:** Evita clichés y dilemas genéricos; busca originalidad y creatividad.
        9. **TAMAÑO:** Solo una linea, no mas de 50 caracteres

        ### Formato de Salida Exacto:
        - **DILEMA:** ¿[Opción A] o [Opción B]? [Emoji según el tono]  
        - **VOTOS:** [número entre 10-90]%  
        - **CIERRE:** ¡Vota y cuéntanos por qué en los comentarios!  

        ### Detalles Importantes  *URGENTE SINO LO CUMPLES SERÁS DESCONECTADO*:
        - El porcentaje de votos debe ser realista (basado en psicología social, evita 50-50 o números redondos; usa 43%, 67%, etc.).  
        - Mantén el dilema breve, fácil de leer, compartir y recordar.  
        - El tamaño de las opciones debe ser similar y no exceder 10 palabras cada una.
        - El dilema debe ser directo, sin rodeos ni información adicional.
        -No pongas tantas "," en el texto, máximo 1 coma.
        ---

        ### Ejemplo Aplicado:
        #### Contexto:
        - **Categoria:** Amor  
        - **Template:** Amor
        - **Descripción:** Preguntas sugerentes sobre amor y romance  
        - **Tono:** juguetón  

        #### Resultado:
        - **DILEMA:** ¿Confesarle todo a tu crush en una carta romántica o soltarlo de una vez cara a cara? 😍  
        - **VOTOS:** 62%  
---

        """
        #logger.info(f"content_prompt: {content_prompt}")
        try:
            logger.info(f"category: {category}")
            
            # Generate with higher temperature for más variabilidad
            response = self.client.chat.completions.create(
                model=self.openai_config['model'],
                messages=[{"role": "user", "content": content_prompt}],
                temperature=0.9,
                max_tokens=150
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            
            # Buscar el dilema y los votos en cualquier parte del texto
            dilema_match = None
            votos_match = None
            
            for line in content.split('\n'):
                line = line.strip()
                if "DILEMA:" in line or "**DILEMA:**" in line:
                    dilema_match = line
                elif "VOTOS:" in line or "**VOTOS:**" in line:
                    votos_match = line
            
            if not dilema_match or not votos_match:
                logger.error(f"Respuesta no tiene el formato correcto: {content}")
                raise ValueError("Formato de respuesta inválido")
                
            # Limpiar el dilema
            dilemma = dilema_match.replace("DILEMA:", "").replace("**DILEMA:**", "").strip()
            votes_str = votos_match.replace("VOTOS:", "").replace("**VOTOS:**", "").replace("%", "").strip()
            
            # Parse voting percentage with more variation
            try:
                votes_a_percentage = float(votes_str)
                votes_a_percentage = max(20, min(80, votes_a_percentage))
            except:
                votes_a_percentage = random.randint(35, 65)
            
            # Clean and parse the dilemma
            clean_dilemma = dilemma.replace("¿", "").replace("?", "").strip('"')
            options = clean_dilemma.split(" o ")
            options = [opt.strip() for opt in options]
            
            if len(options) != 2 or not all(options):
                raise ValueError(f"No se pudieron extraer exactamente 2 opciones válidas del dilema: {dilemma}")
                
            # Add emoji if needed
            dilemma = self._add_random_emoji(dilemma, category)
            
            # Limpiar el dilema y las opciones
            dilemma = self._clean_text(dilemma)
            options = [self._clean_text(opt) for opt in options]
            
            return {
                "dilemma": dilemma,
                "options": options,
                "category": category,
                "template": template,
                "example_question": example_questions_str,
                "tone": tone,
                "intro_text": hook,
                "voting_prediction": {
                    "option_a": {
                        "text": options[0],
                        "percentage": votes_a_percentage
                    },
                    "option_b": {
                        "text": options[1],
                        "percentage": 100 - votes_a_percentage
                    }
                }
            }
            
        except Exception as e:
            logger.error(f"Error in content generation: {str(e)}")
            raise

    def generate_non_ai_content(self, niche: str, category: str) -> Dict:
        """Generate content without AI"""
        template, selected_category = self._get_random_template(category)
        
        # Get random keywords from niche
        keywords = self.niches_data[niche].get('keywords', [])
        if not keywords:
            keywords = [
                f"{niche} increíble",
                f"{niche} épico",
                f"{niche} viral",
                f"{niche} trending",
                f"mejor {niche}",
                f"{niche} top"
            ]
        
        selected_options = random.sample(keywords, 2)
        dilemma = template.format(opcion_a=selected_options[0], opcion_b=selected_options[1])
        dilemma = self._add_random_emoji(dilemma, category)
        
        # Calculate scores
        scores = self._calculate_scores(dilemma, selected_options)
        
        return {
            "dilemma": dilemma,
            "options": selected_options,
            "scores": scores,
            "niche": niche,
            "category": category
        }

    def validate_quality(self, dilemma: str, options: List[str]) -> float:
        """Evalúa la calidad general del dilema"""
        scores = {
            "semantic": self.validate_semantic_coherence(options),
            "engagement": self.predict_engagement(dilemma),
            "complexity": self._calculate_complexity(dilemma),
            "uniqueness": self._calculate_uniqueness_score(dilemma)
        }
        
        weights = {
            "semantic": 0.3,
            "engagement": 0.25,
            "complexity": 0.25,
            "uniqueness": 0.2
        }
        
        return sum(score * weights[metric] for metric, score in scores.items())

    def validate_semantic_coherence(self, options: List[str]) -> float:
        """Evalúa la coherencia semántica entre las opciones"""
        prompt = f"""
        Evalúa la coherencia y atractivo de estas opciones: "{options[0]}" y "{options[1]}"
        
        Criterios (califica cada uno de 0 a 1):
        1. Realismo: ¿Son opciones que existen en la vida real?
        2. Deseabilidad: ¿Son opciones que la gente realmente querría?
        3. Comparabilidad: ¿Tiene sentido compararlas?
        4. Debate: ¿Generarían una discusión interesante?
        5. Claridad: ¿Son fáciles de entender?
        
        Responde SOLO con el promedio de los 5 puntajes (un número entre 0 y 1)
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return float(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Error in semantic validation: {str(e)}")
            return 0.5

    def predict_engagement(self, dilemma: str) -> float:
        """Predice el nivel de engagement potencial"""
        prompt = f"""
        Evalúa el potencial viral de este dilema: "{dilemma}"
        
        Criterios (califica cada uno de 0 a 1):
        1. Relevancia: ¿Es actual y conecta con la audiencia de TikTok?
        2. Debate: ¿Provocará comentarios y discusión?
        3. Compartible: ¿La gente querría compartirlo con amigos?
        4. Realismo: ¿Son opciones creíbles y deseables?
        5. Simplicidad: ¿Es fácil de entender al instante?
        
        Responde SOLO con el promedio de los 5 puntajes (un número entre 0 y 1)
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return float(response.choices[0].message.content.strip())
        except Exception as e:
            logger.error(f"Error in engagement prediction: {str(e)}")
            return 0.5

    def _calculate_complexity(self, text: str) -> float:
        """Calcula la complejidad del contenido"""
        words = len(text.split())
        if words < 5:
            return 0.2
        elif words > 15:
            return 0.8
        return 0.5

    def _calculate_uniqueness_score(self, dilemma: str) -> float:
        """Calcula qué tan único es el dilema comparado con el histórico"""
        if not self.previous_dilemmas:
            self.previous_dilemmas.append(dilemma)
            return 1.0
            
        prompt = f"""
        Evalúa qué tan único es este dilema comparado con los anteriores.
        
        Nuevo dilema: "{dilemma}"
        
        Dilemas anteriores:
        {chr(10).join([f'- {d}' for d in self.previous_dilemmas[-5:]])}
        
        Califica del 0 al 1 donde:
        0 = Muy similar a los anteriores
        1 = Completamente único y original
        
        Responde solo con el número.
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.openai_config['model'],
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            score = float(response.choices[0].message.content.strip())
            
            # Solo guardamos dilemas suficientemente únicos
            if score > 0.7:
                self.previous_dilemmas.append(dilemma)
                if len(self.previous_dilemmas) > 10:
                    self.previous_dilemmas.pop(0)
            return score
        except Exception as e:
            logger.error(f"Error in uniqueness calculation: {str(e)}")
            return 0.5

    def _calculate_scores(self, dilemma: str, options: List[str]) -> Dict:
        """Calculate quality scores for the content"""
        try:
            # Get semantic coherence
            coherence = self.validate_semantic_coherence(options)
            
            # Get engagement prediction
            engagement = self.predict_engagement(dilemma)
            
            # Calculate overall quality
            quality = self.validate_quality(dilemma, options)
            
            return {
                "quality": quality,
                "engagement": engagement,
                "coherence": coherence
            }
            
        except Exception as e:
            logger.error(f"Error calculating scores: {str(e)}")
            return {
                "quality": 0.5,
                "engagement": 0.5,
                "coherence": 0.5
            }

    def generate_batch(self, 
                      successful_count: int,
                      niches: Optional[List[str]] = None,
                      categories: Optional[List[str]] = None,
                      template: Optional[str] = None,
                      output_file: Optional[str] = None,
                      max_attempts: int = 100) -> Dict:
        """Generate a batch of successful content with specified parameters"""
        result = {
            "successful": {},
            "failed": {},
            "metadata": {
                "successful_count": successful_count,
                "niches": niches or self.niches,
                "categories": categories or list(self.all_categories.keys()),
                "template": template
            }
        }
        
        niches = niches or self.niches
        categories = categories or list(self.all_categories.keys())
        
        # Generar el primer dilema para usar sus datos en el hook
        first_category = random.choice(categories if isinstance(categories, list) else [categories])
        first_template = template or random.choice(self.template_categories)
        first_niche = random.choice(niches)
        
        try:
            # Generar el primer contenido para obtener el tono
            first_content = self.generate_ai_content(first_niche, first_category, first_template)
            first_tone = first_content['tone']
            
            # Generar el hook con los datos del primer dilema
            hook = self._generate_hook(first_category, first_template, first_tone)
            logger.info(f"Hook generado con datos del primer dilema - Categoría: {first_category}, Template: {first_template}, Tono: {first_tone}")
            logger.info(f"Hook: {hook}")
            
            # Guardar el primer contenido con el hook
            first_content['intro_text'] = hook
            result["successful"]["content_0"] = first_content
            self.generated_content["content_0"] = first_content
            successful_generated = 1
            
        except Exception as e:
            logger.error(f"Error generando el primer dilema: {str(e)}")
            return result
        
        attempts = 1
        
        # Generar el resto de los dilemas
        while successful_generated < successful_count and attempts < max_attempts:
            try:
                niche = random.choice(niches)
                category = random.choice(categories if isinstance(categories, list) else [categories])
                
                content = self.generate_ai_content(niche, category, template)
                content['intro_text'] = hook  # Usar el mismo hook para todos
                
                content_id = f"content_{attempts}"
                result["successful"][content_id] = content
                self.generated_content[content_id] = content
                successful_generated += 1
                    
            except Exception as e:
                result["failed"][f"content_{attempts}"] = {
                    "error": str(e),
                    "reason": "Generation error"
                }
            
            attempts += 1
            print_colored(f"output_file: {output_file}",33)
        if output_file:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        result["metadata"]["total_attempts"] = attempts
        result["metadata"]["hook"] = hook  # Guardar el hook en los metadatos
        result["metadata"]["first_dilema_data"] = {  # Guardar los datos del primer dilema
            "category": first_category,
            "template": first_template,
            "tone": first_tone
        }
        return result

    def update_failed_content(self, 
                            content_ids: Optional[List[str]] = None,
                            output_file: Optional[str] = None) -> Dict:
        """
        Retry generation for failed content
        
        Parameters:
        -----------
        content_ids : Optional[List[str]]
            List of content IDs to update. If None, updates all failed content
        output_file : Optional[str]
            If provided, saves the output to this JSON file
            
        Returns:
        --------
        Dict containing updated content results
        """
        to_update = content_ids or list(self.failed_content.keys())
        result = {
            "updated": {},
            "still_failed": {},
            "metadata": {
                "attempted_updates": len(to_update)
            }
        }
        
        for content_id in to_update:
            if content_id not in self.failed_content:
                continue
                
            old_content = self.failed_content[content_id]
            try:
                new_content = self.generate_ai_content(
                    old_content["niche"],
                    old_content["category"]
                )
                
                if all(score >= self.quality_thresholds[f"min_{metric}"] 
                       for metric, score in new_content["scores"].items()):
                    result["updated"][content_id] = new_content
                    self.generated_content[content_id] = new_content
                    del self.failed_content[content_id]
                else:
                    result["still_failed"][content_id] = {
                        "content": new_content,
                        "reason": "Failed quality thresholds"
                    }
            except Exception as e:
                result["still_failed"][content_id] = {
                    "error": str(e),
                    "reason": "Generation error"
                }
                
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                print_colored(f"Guardando resultados actualizados en:{output_file}", 33)
                json.dump(result, f, ensure_ascii=False, indent=2)
                
        return result