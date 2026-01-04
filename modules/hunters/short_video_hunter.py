import os
import warnings

# Suprimir advertencia de versión de Python de yt-dlp
# IMPORTANTE: Esto debe ejecutarse antes de cualquier funcionalidad de yt-dlp que provoque la advertencia.
warnings.filterwarnings("ignore", message="Support for Python version 3.9 has been deprecated")

import cv2
import yt_dlp
import uuid
import glob
import numpy as np
from PIL import Image
from datetime import datetime
from modules.integration.storage import get_storage_provider
from modules.brains.vision_engine import VisionEngine

class ShortVideoHunter:
    """
    Cazador de Videos Cortos (Shorts/Reels).
    
    Este módulo imita la funcionalidad de buscar tendencias en TikTok/Reels utilizando 
    YouTube Shorts como fuente proxy, lo cual es más estable y escalable que scrapear TikTok directamente.
    
    Funcionalidades principales:
    1. Busca videos verticales cortos (YouTube Shorts) relacionados con una etiqueta (tag).
    2. Filtrado Inteligente de Video:
       - Filtra por duración (< 120s).
       - Descompone el video en frames.
       - Analiza cada frame con IA (VisionEngine) para asegurar relevancia (moda/ropa).
       - Exige un MÍNIMO de 5 frames válidos por video para aceptarlo.
    3. Sube solo las imágenes validadas al sistema de almacenamiento.
    """

    def __init__(self):
        # Inicializar proveedor de almacenamiento (S3, Local, etc.)
        self.storage = get_storage_provider()
        
        # Inicializar Vision Engine para filtrado de contenido de frames
        self.vision = VisionEngine()
        
        # Directorio temporal para descargar los videos antes de procesarlos.
        # Se asegura de crear la carpeta si no existe.
        self.temp_dir = "temp_video_downloads"
        os.makedirs(self.temp_dir, exist_ok=True)

    def hunt(self, tag: str, limit: int = 5):
        """
        Método principal para buscar, descargar y procesar videos cortos.
        
        Args:
            tag (str): Término de búsqueda o hashtag (ej. "Summer Fashion").
            limit (int): Número objetivo de VIDEOS COMPLETOS a procesar (cada uno aportará >= 5 frames).
            
        Returns:
            list: Lista de diccionarios con la metadata de los frames extraídos.
        """
        print(f"📹 [ShortVideoHunter] Iniciando búsqueda para el tag: '{tag}'")
        
        results = []
        successful_videos_count = 0
        
        # Configuración de yt-dlp
        ydl_opts = {
            'format': 'best[ext=mp4]',     # Preferir MP4
            'outtmpl': os.path.join(self.temp_dir, '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'concurrent_fragment_downloads': 1,
            'nowarnings': True,
        }

        # Construcción de query: Pedimos 'limit * 10' para tener un buffer grande,
        # ya que descartaremos videos que no cumplan el requisito de frames mínimos.
        search_query = f"ytsearch{limit*10}:{tag} #shorts" 

        print(f"⬇️ [ShortVideoHunter] Buscando candidatos para obtener {limit} videos válidos...")
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Extracción de Metadatos
                info = ydl.extract_info(search_query, download=False)
                
                if 'entries' in info:
                    all_entries = info['entries']
                else:
                    all_entries = [info]

                # 2. Filtrado por Duración (< 120s)
                filtered_entries = []
                for entry in all_entries:
                    if not entry: continue
                    duration = entry.get('duration', 0)
                    if 0 < duration < 120: 
                        filtered_entries.append(entry)
                
                print(f"   ℹ️ Candidatos por duración (<120s): {len(filtered_entries)}")

                # 3. Proceso de Caza (Descarga -> Análisis -> Aprobación)
                for entry in filtered_entries:
                    # Si ya cumplimos la cuota de videos exitosos, terminamos.
                    if successful_videos_count >= limit:
                        break
                        
                    video_id = entry.get('id')
                    video_url = entry.get('webpage_url') or entry.get('url')
                    
                    print(f"   ⬇️ Probando video {video_id} ({entry.get('duration')}s)...")
                    
                    try:
                        # Descargar
                        ydl.download([video_url or video_id])
                        
                        # Localizar archivo
                        candidates = glob.glob(os.path.join(self.temp_dir, f"{video_id}.*"))
                        if candidates:
                            video_path = candidates[0]
                            
                            # 4. Procesamiento Visual y Filtrado de Frames
                            frames = self._process_video(video_path, parent_id=video_id, tag=tag)
                            
                            # Lógica crítica: Solo aceptamos el video si conseguimos al menos 5 buenos frames
                            if len(frames) >= 5:
                                results.extend(frames)
                                successful_videos_count += 1
                                print(f"      ✅ Video ACEPTADO. Frames extraídos: {len(frames)}. Progreso: {successful_videos_count}/{limit}")
                            else:
                                print(f"      🗑️ Video DESCARTADO. Insuficientes frames válidos ({len(frames)} < 5).")
                            
                            # Limpieza
                            if os.path.exists(video_path):
                                os.remove(video_path)
                        else:
                             print(f"   ⚠️ Archivo no encontrado tras descarga: {video_id}")

                    except Exception as e:
                        print(f"   ❌ Error procesando {video_id}: {e}")
                        continue

        except Exception as e:
            print(f"❌ [ShortVideoHunter] Error crítico: {e}")

        print(f"🏁 [ShortVideoHunter] Caza terminada. {successful_videos_count} videos procesados, {len(results)} frames totales.")
        return results

    def _process_video(self, video_path: str, parent_id: str, tag: str) -> list:
        """
        Lee el video, extrae frames, los filtra con IA y guarda solo los válidos.
        
        Args:
           video_path: Ruta archivo.
           parent_id: ID.
           tag: Tag.
           
        Returns:
           list: Lista de objetos resultado (solo si se superó el umbral en 'hunt', 
                 pero aquí retornamos todos los válidos encontrados para que 'hunt' decida).
        """
        # print(f"      🎞️ Analizando frames de: {os.path.basename(video_path)}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps == 0: fps = 30 

        # Extraer 1 frame cada 1.5 segundos (un poco más frecuente para tener más oportunidades de pasar el filtro)
        sample_rate_sec = 1.5
        valid_frames_exctracted = []
        # Lista para almacenar histogramas de los frames aceptados
        accepted_histograms = []
        current_frame_idx = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break 
            
            if current_frame_idx % frame_interval == 0:
                # 1. Verificación de Duplicados por Histograma de Color (Semántico)
                # El usuario quiere evitar "misma persona, misma ropa, distinta pose".
                # El dHash falla aquí porque la pose cambia la estructura.
                # El Histograma de Color (Hue/Saturation) es invariante a la pose: si la ropa es roja, el histograma será rojo.
                try:
                    current_hist = self._calculate_histogram(frame)
                    is_duplicate = False
                    
                    for existing_hist in accepted_histograms:
                         # Comparamos correlación (1.0 = idéntico, 0.0 = nada que ver)
                         similarity = cv2.compareHist(current_hist, existing_hist, cv2.HISTCMP_CORREL)
                         
                         # Si la similitud es > 0.85, asumimos que es el mismo outfit/escena.
                         if similarity > 0.85: 
                             is_duplicate = True
                             break
                    
                    if is_duplicate:
                        # print(f"         🔄 Frame descartado por redundancia de color (Mismo outfit).")
                        current_frame_idx += 1
                        continue
                except Exception as e:
                    print(f"      ⚠️ Warning: Falló cálculo de histograma ({e}). Continuando.")

                # 2. Análisis de IA
                # Convertir BGR (OpenCV) a RGB (PIL) para el VisionEngine
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(frame_rgb)
                
                # Filtrar con IA
                if self._is_relevant_frame(pil_image):
                    # Si es válido, lo codificamos para subir
                    # Volvemos a usar 'frame' (BGR) para encoding JPG correcto
                    success, buffer = cv2.imencode(".jpg", frame)
                    if success:
                        file_name = f"shorts_{parent_id}_{current_frame_idx}.jpg"
                        
                        # Subir
                        stored_url = self.storage.upload_file(buffer.tobytes(), file_name)
                        
                        valid_frames_exctracted.append({
                            "s3_url": stored_url,
                            "parent_video": parent_id,
                            "tag": tag,
                            "timestamp": datetime.now().isoformat()
                        })
                        
                        # Registrar el histograma de este frame exitoso
                        accepted_histograms.append(current_hist)
            
            current_frame_idx += 1
        
        cap.release()
        return valid_frames_exctracted

    def _calculate_histogram(self, image):
        """
        Calcula el histograma de color HSV de una imagen.
        Usamos HSV (Hue, Saturation) porque es más estable a cambios de iluminación que RGB.
        """
        # Convertir a HSV
        hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Calcular histograma para los canales Hue (0) y Saturation (1)
        # Bins: 50 para Hue, 60 para Saturation (ajustable para precisión)
        # Rangos: Hue [0, 180], Saturation [0, 256]
        hist = cv2.calcHist([hsv_image], [0, 1], None, [50, 60], [0, 180, 0, 256])
        
        # Normalizar el histograma (importante para compareHist)
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        return hist

    def _is_relevant_frame(self, image: Image.Image) -> bool:
        """
        Filtro de IA más permisivo que PinterestHunter, pero descarta basura.
        """
        candidates = {
            "content_type": [
                # Positivos (Incluimos 'person wearing clothes' que es muy común en video)
                "person wearing clothes",
                "fashion outfit",
                "editorial fashion photography",
                "street style photography",
                
                # Negativos
                "promotional graphic with text",
                "digital collage with text",
                "text overlay",
                "blurry or low quality image",  # Nuevo negativo para video
                "close-up of face only"         # Evitar selfies sin ropa visible
            ]
        }
        
        analysis = self.vision.analyze(image, candidates)
        if not analysis or "content_type" not in analysis:
            return False
            
        best = analysis["content_type"]["label"]
        score = analysis["content_type"]["score"]
        
        allowed = [
            "person wearing clothes", 
            "fashion outfit", 
            "editorial fashion photography",
            "street style photography"
        ]
        
        # Umbral 0.25 (ligeramente más estricto que 0.2, pero permisivo)
        is_valid = best in allowed and score > 0.25
        
        return is_valid

if __name__ == "__main__":
    hunter = ShortVideoHunter()
    hunter.hunt("Summer Fashion Trends 2025", limit=1)
