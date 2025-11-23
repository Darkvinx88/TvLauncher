import os
from pathlib import Path

import requests

# === IMAGE MANAGER CLASS ===
class ImageManager:
    """Gestisce il download e la cache delle immagini per le app"""
    
    def __init__(self, assets_dir="assets", api_key=None):
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(exist_ok=True)
        self.api_key = api_key
        
    def get_app_image(self, app_name, app_path):
        """
        Ottiene l'immagine per un'app.
        Cerca prima in locale, poi online se necessario.
        """
        # 1. Cerca in locale
        local_image = self._find_local_image(app_name)
        if local_image:
            return str(local_image)
        
        # 2. Cerca online (se API key disponibile e requests installato)
        if self.api_key:
            online_image = self._download_from_steamgriddb(app_name)
            if online_image:
                return str(online_image)
        
        # 3. Fallback su icona exe
        return app_path if app_path and os.path.exists(app_path) else None
    
    def _find_local_image(self, app_name):
        """Cerca immagine nella cartella assets locale"""
        safe_name = self._sanitize_filename(app_name)
        app_folder = self.assets_dir / safe_name
        
        if app_folder.exists():
            for ext in ['.png', '.jpg', '.jpeg', '.webp']:
                image_path = app_folder / f"banner{ext}"
                if image_path.exists():
                    return image_path
                
                image_path = app_folder / f"{safe_name}{ext}"
                if image_path.exists():
                    return image_path
        
        return None
    
    def _download_from_steamgriddb(self, app_name):
        """Scarica immagine da SteamGridDB"""
        if not self.api_key:
            return None
        
        try:
            from urllib.parse import quote
            headers = {"Authorization": f"Bearer {self.api_key}"}
            
            # 1. Cerca il gioco
            search_url = f"https://www.steamgriddb.com/api/v2/search/autocomplete/{quote(app_name)}"
            response = requests.get(search_url, headers=headers, timeout=5)
            
            if response.status_code != 200:
                return None
            
            results = response.json()
            if not results.get('data'):
                return None
            
            game_id = results['data'][0]['id']
            
            # 2. Ottieni immagini 16:9
            grids_url = f"https://www.steamgriddb.com/api/v2/grids/game/{game_id}"
            params = {
                "dimensions": ["460x215", "920x430"],
                "types": ["static"]
            }
            grids_response = requests.get(grids_url, headers=headers, params=params, timeout=5)
            
            if grids_response.status_code != 200:
                return None
            
            grids = grids_response.json()
            if not grids.get('data'):
                return None
            
            # 3. Scarica la prima immagine
            image_url = grids['data'][0]['url']
            image_data = requests.get(image_url, timeout=10).content
            
            # 4. Salva in locale
            safe_name = self._sanitize_filename(app_name)
            app_folder = self.assets_dir / safe_name
            app_folder.mkdir(exist_ok=True)
            
            ext = '.png' if 'png' in image_url.lower() else '.jpg'
            image_path = app_folder / f"banner{ext}"
            
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            print(f"✅ Downloaded image for: {app_name}")
            return image_path
            
        except Exception as e:
            print(f"❌ Error downloading image for {app_name}: {e}")
            return None
    
    def _sanitize_filename(self, name):
        """Rimuove caratteri non validi per nomi file"""
        safe = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        return safe.strip().replace(' ', '_')
