# ==================================
# === NUOVO WORKER PER DOWNLOAD ===
# ==================================
from PyQt6.QtCore import QThread, pyqtSignal


class DownloadWorker(QThread):
    """Worker thread per scaricare immagini in background"""
    progress_update = pyqtSignal(str, int) # Messaggio, percentuale
    app_ready = pyqtSignal(dict) # Invia un'app completa
    finished = pyqtSignal()

    def __init__(self, selected_programs, image_manager, existing_app_names):
        super().__init__()
        self.selected = selected_programs
        self.image_manager = image_manager
        self.existing = existing_app_names
        self.is_running = True

    def run(self):
        # Filtra solo i programmi non già esistenti
        to_download = []
        for prog in self.selected:
            if prog['name'].lower() not in self.existing:
                 to_download.append(prog)
        
        total = len(to_download)
        if total == 0:
            self.progress_update.emit("Programs already present.", 100)
            self.finished.emit()
            return

        for i, prog in enumerate(to_download):
            if not self.is_running:
                break
            
            percent = int((i + 1) / total * 100)
            self.progress_update.emit(f"Downloading: {prog['name']}...", percent)
            
            # Scarica immagine 16:9 (se API key c'è)
            if self.image_manager.api_key:
                image_result = self.image_manager.get_app_image(prog['name'], prog['path'])
                if image_result:
                    prog['icon'] = image_result
            
            self.app_ready.emit(prog) # Invia l'app al thread principale
        
        if self.is_running:
            self.progress_update.emit("Completated!", 100)
        else:
            self.progress_update.emit("Cancel.", 100)
            
        self.finished.emit()

    def stop(self):
        """Ferma il worker in modo sicuro"""
        print("Worker Interruption Requested")
        self.is_running = False