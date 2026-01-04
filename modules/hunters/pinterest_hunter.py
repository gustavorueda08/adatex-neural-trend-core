import time
import uuid
import requests
import io
import random
from datetime import datetime
from PIL import Image
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from modules.integration.storage import get_storage_provider
from modules.brains.vision_engine import VisionEngine
from selenium.common.exceptions import StaleElementReferenceException

class PinterestHunter:
    """
    Cazador de tendencias para Pinterest (Módulo de Scraping + IA).
    
    Este módulo se encarga de:
    1.  Navegar automáticamente por Pinterest usando Selenium.
    2.  Realizar búsquedas y "scroll infinito" para cargar contenido dinámico.
    3.  Extraer las URLs de las imágenes encontradas.
    4.  Filtrar imágenes irrelevantes (texto, anuncios) usando Inteligencia Artificial (VisionEngine).
    5.  Descargar y almacenar solo las imágenes de alta calidad validadas.
    """
    def __init__(self):
        # Inicializar el proveedor de almacenamiento configurado (S3, disco local, etc.)
        self.storage = get_storage_provider()
        
        # Inicializar el Motor de Visión (IA) para análisis y filtrado de contenido visual.
        # Esto cargará el modelo CLIP/SigLIP en memoria.
        self.vision = VisionEngine()
        
        # Configuración de opciones para el navegador Chrome (Selenium)
        self.options = Options()
        # 'no-sandbox' y 'disable-dev-shm-usage' son críticos para entornos Docker/Linux con recursos limitados.
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        
        # Intenta ocultar que el navegador está siendo controlado por un script de automatización
        # para evitar detecciones y bloqueos simples por parte de Pinterest.
        self.options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Define un User-Agent de navegador real (Mac OS) para simular tráfico legítimo.
        self.options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
    def hunt(self, query: str, limit: int = 10):
        """
        Ejecuta el proceso completo de "caza" (búsqueda, filtrado y descarga).
        
        El flujo garantiza que se obtengan `limit` imágenes VÁLIDAS, no solo procesadas.
        
        Args:
            query (str): Término de búsqueda (ej. "Summer 2025 Fashion").
            limit (int): Número objetivo de imágenes válidas a descargar.
            
        Returns:
            list: Lista de diccionarios con metadatos de las imágenes capturadas.
        """
        print(f"🕵️‍♀️ [PinterestHunter] Iniciando caza para: '{query}'")
        try:
            # Intentar instalar automáticamente el driver de Chrome compatible con la versión del navegador instalada.
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=self.options)
        except Exception as e:
            print(f"⚠️ [PinterestHunter] Falló init del driver con manager, intentando default: {e}")
            # Si falla el gestor automático (común en algunos servidores), intentamos usar el driver del sistema.
            driver = webdriver.Chrome(options=self.options)
        
        results = []
        unique_urls = set()       # Registro de URLs ya descargadas para evitar duplicados exactos.
        visited_raw_urls = set()  # Registro de URLs de origen (thumbnails) para no procesar la misma imagen dos veces.
        
        try:
            # 1. Navegación Inicial
            # Construimos la URL de búsqueda y navegamos a ella.
            search_url = f"https://www.pinterest.com/search/pins/?q={query}"
            driver.get(search_url)
            time.sleep(5) # Espera explícita para asegurar la carga del "esqueleto" de la página.
            
            # 2. Bucle de Scroll Infinito
            scrolls = 0
            # Aumentamos agresivamente los intentos de scroll.
            # Como el filtro es estricto, necesitamos ver MUCHAS imágenes para encontrar las válidas.
            # Factor 5x: Para encontrar 10 imágenes, estamos dispuestos a scrollear 50 veces.
            max_scrolls = max(60, limit * 5)
            
            # El bucle continúa MIENTRAS:
            # a) No hayamos alcanzado el número deseado de resultados (len(results) < limit)
            # b) Y no hayamos excedido el límite de intentos de scroll.
            while len(results) < limit and scrolls < max_scrolls:
                print(f"📜 [PinterestHunter] Scroll {scrolls+1}/{max_scrolls} | Válidos: {len(results)}/{limit}")
                
                # Ejecutar JavaScript para hacer scroll hasta el fondo absoluto de la página actual.
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                # Pausa variable: aumentar un poco el tiempo máximo para dar margen a redes lentas
                time.sleep(random.uniform(2, 5))
                
                # 3. Extracción de Elementos del DOM
                # Buscamos todas las etiquetas <img> presentes en la página tras el scroll.
                # IMPORTANTE: Extraemos las URLs (src) inmediatamente a una lista de strings.
                # Si iteramos sobre los objetos WebElement (img) direcatmente mientras hacemos operaciones lentas
                # (descargas/IA), el DOM puede cambiar (virtualización) y provocar 'StaleElementReferenceException'.
                try:
                    current_images = driver.find_elements(By.TAG_NAME, "img")
                    # Captura robusta de URLs ignorando elementos que desaparecen instantáneamente
                    raw_srcs = []
                    for img in current_images:
                        try:
                            src = img.get_attribute("src")
                            if src:
                                raw_srcs.append(src)
                        except StaleElementReferenceException:
                            continue # El elemento desapareció, lo ignoramos
                except Exception as e:
                    print(f"⚠️ [PinterestHunter] Error leyendo DOM: {e}")
                    raw_srcs = []
                
                for raw_src in raw_srcs:
                    # Verificación rápida: si ya cumplimos la cuota en medio del procesamiento de este lote, paramos.
                    if len(results) >= limit:
                        break
                        
                    # Validar que la URL es nueva
                    if raw_src in visited_raw_urls:
                        continue
                    visited_raw_urls.add(raw_src)
                    
                    # 4. Filtrado de Ruido Básico (basado en URL)
                    # Pinterest usa sufijos como /75x75/ para avatares de usuarios. Los descartamos inmediatamente.
                    if "/75x75/" in raw_src or "/60x60/" in raw_src:
                        continue
                        
                    # 5. Lógica de "Mejora de Resolución"
                    # Pinterest sirve miniaturas (/236x/). Aquí intentamos deducir la URL de la imagen original.
                    candidates = []
                    if "/236x/" in raw_src:
                        # Prioridad 1: '/originals/' es la imagen subida originalmente (máxima calidad).
                        candidates.append(raw_src.replace("/236x/", "/originals/"))
                        # Prioridad 2: '/564x/' es una versión de alta calidad estándar.
                        candidates.append(raw_src.replace("/236x/", "/564x/"))
                        # Prioridad 3: Fallback a la miniatura original si las otras fallan.
                        candidates.append(raw_src) 
                    else:
                        candidates.append(raw_src)
                    
                    # Intentar descargar la imagen probando los candidatos en orden de calidad.
                    image_bytes = None
                    successful_url = None
                    
                    for url in candidates:
                        if url in unique_urls: 
                            continue # Ya tenemos esta URL exacta guardada.
                        
                        try:
                            # Descargamos a memoria (BytesIO) para analizar sin guardar en disco todavía.
                            image_bytes = self._download_image(url)
                            successful_url = url
                            break # ¡Éxito! Salimos del bucle de candidatos.
                        except Exception:
                            # Si falla (ej. 404 porque no existe '/originals/'), probamos el siguiente candidato.
                            continue
                    
                    if not image_bytes or not successful_url:
                        continue

                    # 6. Filtrado Inteligente con Vision Engine (IA)
                    # Aquí es donde aplicamos el filtro semántico solicitado por el usuario.
                    try:
                        # Convertimos bytes a objeto PIL Image para que la IA pueda "verlo".
                        pil_image = Image.open(image_bytes)
                        
                        # Llamamos al método de validación que usa Zero-Shot classification.
                        if not self._is_relevant_image(pil_image, query):
                            # Si la IA dice que es texto, un banner o irrelevante, la descartamos.
                            # debug: print(f"   🗑️ Descartada por filtro IA.")
                            continue
                    except Exception as e:
                        print(f"   ⚠️ [PinterestHunter] Error analizando imagen (IA): {e}")
                        continue
                        
                    # Si llegamos aquí, la imagen pasó todos los filtros. Registramos la URL final.
                    unique_urls.add(successful_url)
                    
                    # 7. Persistencia y Almacenamiento Final
                    try:
                        # IMPORTANTE: Rebobinar el puntero del archivo en memoria al inicio para poder leerlo de nuevo al subirlo.
                        image_bytes.seek(0)
                        
                        file_name = f"pinterest_{uuid.uuid4().hex[:8]}.jpg"
                        # Subir archivo al storage definitivo.
                        stored_url = self.storage.upload_file(image_bytes, file_name)
                        
                        # Guardar metadatos del resultado.
                        result = {
                            "s3_url": stored_url,
                            "source_url": successful_url,
                            "query": query,
                            "timestamp": datetime.now().isoformat()
                        }
                        results.append(result)
                        print(f"   ✅ [PinterestHunter] Guardado ({len(results)}/{limit}): {stored_url}")
                        
                    except Exception as e:
                        print(f"⚠️ [PinterestHunter] Error al guardar en storage {successful_url}: {e}")
                        continue
                
                scrolls += 1
                
        except Exception as e:
            print(f"❌ [PinterestHunter] Error crítico durante la ejecución: {e}")
        finally:
            # Siempre cerrar el navegador, incluso si hubo error, para evitar zombis de Chrome.
            driver.quit()
        
        print(f"🏁 [PinterestHunter] Caza terminada. Capturados {len(results)} assets válidos.")
        return results

    def _is_relevant_image(self, image: Image.Image, query: str) -> bool:
        """
        Analiza el contenido visual de la imagen usando VisionEngine para determinar si es relevante.
        
        Utiliza clasificación Zero-Shot para distinguir entre fotos reales de moda y gráficos/texto basura.
        """
        # Definir categorías semánticas refinadas para mejorar el filtrado.
        # Basado en pruebas, "editorial fashion photography" funciona mejor para capturar
        # imágenes reales de alta calidad, mientras que las categorías negativas específicas
        # ayudan a descartar collages y banners promocionales que antes se colaban.
        candidates = {
            "content_type": [
                # Categorías Positivas (Lo que queremos)
                "editorial fashion photography",   # Foto de moda estilo editorial (alta calidad).
                "street style photography",        # Foto de estilo callejero (personas reales).
                "clothing product photography",    # Foto de producto limpia.

                # Categorías Negativas (Lo que queremos evitar)
                "promotional graphic with text",   # Gráficos con texto de venta/promo.
                "digital collage with text",       # Collages de varias fotos + texto (muy común en Pinterest).
                "infographic layout",              # Infografías o guías de estilo con mucho texto.
                "text overlay"                     # Imágenes donde el texto tapa la ropa.
            ]
        }
        
        # Ejecutar inferencia en el VisionEngine. Retorna las probabilidades.
        analysis = self.vision.analyze(image, candidates)
        
        if not analysis or "content_type" not in analysis:
            return False
            
        best_match = analysis["content_type"]["label"]
        score = analysis["content_type"]["score"]
        
        # Lista blanca de categorías aceptadas.
        allowed_types = [
            "editorial fashion photography",
            "street style photography", 
            "clothing product photography"
        ]
        
        # La imagen es válida SI:
        # 1. Su categoría más probable está en la lista blanca.
        # 2. La confianza del modelo es mayor a 0.2 (20%).
        #    Nota: El umbral es bajo (0.2) porque al tener categorías negativas tan fuertes (ej. collage con 0.8),
        #    si una imagen real gana aunque sea con 0.3, es suficiente para confirmar que NO es un collage.
        is_valid = best_match in allowed_types and score > 0.2 
        
        return is_valid

    def _download_image(self, url: str) -> io.BytesIO:
        """
        Realiza la petición HTTP para descargar los bytes de la imagen.
        Utiliza 'stream=True' para manejo eficiente de memoria.
        """
        headers = {
            # User-Agent necesario para que el servidor de imágenes no rechace la petición (403 Forbidden).
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        # Timeout de 10s para evitar bloqueos si la red está lenta.
        response = requests.get(url, headers=headers, stream=True, timeout=10)
        response.raise_for_status() # Lanza error si el status code no es 200 OK.
        return io.BytesIO(response.content)

if __name__ == "__main__":
    # Bloque de prueba para ejecutar este script directamente desde la terminal.
    hunter = PinterestHunter()
    hunter.hunt("Summer 2025 Fashion Trends", limit=3)
