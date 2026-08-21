from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
from pathlib import Path

class SoundManager:
    """Gestisce i suoni di navigazione del launcher"""
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.sounds = {}
        self.assets_dir = Path("assets/sounds")
        self.assets_dir.mkdir(exist_ok=True)
        
        # Carica i suoni disponibili
        self._load_sounds()
    
    def _load_sounds(self):
        """Carica tutti i file audio dalla cartella assets/sounds"""
        sound_files = {
            'navigate': 'navigate.wav',      # Movimento su/giù/sx/dx
            'select': 'select.wav',          # Conferma/Enter
            'back': 'back.wav',              # Esc/Indietro
           
        }
        
        for sound_name, filename in sound_files.items():
            sound_path = self.assets_dir / filename
            if sound_path.exists():
                effect = QSoundEffect()
                effect.setSource(QUrl.fromLocalFile(str(sound_path.absolute())))
                effect.setVolume(0.4)  # Volume di default al 80%
                self.sounds[sound_name] = effect
                
    
    def play(self, sound_name):
        """Riproduce un suono se abilitato"""
        if not self.enabled:
            return
        
        if sound_name in self.sounds:
            self.sounds[sound_name].play()
    
    def set_enabled(self, enabled):
        """Abilita/disabilita i suoni"""
        self.enabled = enabled
    
    def set_volume(self, volume):
        """Imposta il volume globale (0.0 - 1.0)"""
        for sound in self.sounds.values():
            sound.setVolume(volume)
    
    # Metodi di convenienza
    def navigate(self):
        self.play('navigate')
    
    def select(self):
        self.play('select')
    
    def back(self):
        self.play('back')
    
    