
from pathlib import Path
import platform

try:
    from PyQt6.QtMultimedia import QSoundEffect, QAudioOutput, QMediaPlayer
    from PyQt6.QtCore import QUrl
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("⚠️ QtMultimedia not available - sound effects disabled")

IS_LINUX = platform.system() == "Linux"

class SoundManager:
    """
    Gestisce i suoni del launcher
    
    """
    
    def __init__(self, enabled=False):
        self.enabled = enabled
        self.sounds = {}
        
        if not AUDIO_AVAILABLE:
            print("⚠️ Audio support not available")
            return
        
        
        # QSoundEffect ha problemi di gestione memoria su alcuni sistemi Linux
        self.use_media_player = IS_LINUX
        
        if self.use_media_player:
            self._init_media_player()
        else:
            self._init_sound_effects()
    
    def _init_sound_effects(self):
        """Inizializza QSoundEffect (Windows/macOS)"""
        sounds_dir = Path("assets/sounds")
        
        sound_files = {
            'navigate': 'navigate.wav',
            'select': 'select.wav',
            'back': 'back.wav',
        }
        
        for sound_id, filename in sound_files.items():
            sound_path = sounds_dir / filename
            
            if sound_path.exists():
                try:
                    effect = QSoundEffect()
                    effect.setSource(QUrl.fromLocalFile(str(sound_path.absolute())))
                    effect.setVolume(0.5)
                    
                    # Precarica il suono
                    effect.setLoopCount(1)
                    
                    self.sounds[sound_id] = effect
                    
                    
                except Exception as e:
                    print(f"⚠️ Failed to load {sound_id}: {e}")
            else:
                print(f"⚠️ Sound file not found: {sound_path}")
    
    def _init_media_player(self):
        """
         Inizializza QMediaPlayer per Linux
        Più stabile di QSoundEffect su Linux
        """
        sounds_dir = Path("assets/sounds")
        
        sound_files = {
            'navigate': 'navigate.wav',
            'select': 'select.wav',
            'back': 'back.wav',
        }
        
        # Crea un player per ogni suono (evita conflitti)
        for sound_id, filename in sound_files.items():
            sound_path = sounds_dir / filename
            
            if sound_path.exists():
                try:
                    player = QMediaPlayer()
                    audio_output = QAudioOutput()
                    
                    # Collega audio output al player
                    player.setAudioOutput(audio_output)
                    
                    # Imposta il file
                    player.setSource(QUrl.fromLocalFile(str(sound_path.absolute())))
                    
                    # Volume moderato
                    audio_output.setVolume(0.5)
                    
                    # Salva sia il player che l'output
                    self.sounds[sound_id] = {
                        'player': player,
                        'output': audio_output
                    }
                    
                    
                    
                except Exception as e:
                    print(f"⚠️ Failed to load {sound_id}: {e}")
            else:
                print(f"⚠️ Sound file not found: {sound_path}")
    
    def set_enabled(self, enabled):
        """Abilita/disabilita i suoni"""
        self.enabled = enabled
        print(f"🔊 Sound effects: {'ON' if enabled else 'OFF'}")
    
    def navigate(self):
        """Suono di navigazione (movimento)"""
        self._play('navigate')
    
    def select(self):
        """Suono di selezione/conferma"""
        self._play('select')
    
    def back(self):
        """Suono di ritorno/annulla"""
        self._play('back')
    
    def _play(self, sound_id):
        """
        Riproduce un suono con gestione separata per Linux
        """
        if not self.enabled or not AUDIO_AVAILABLE:
            return
        
        if sound_id not in self.sounds:
            return
        
        try:
            if self.use_media_player:
                #  Usa QMediaPlayer
                sound_data = self.sounds[sound_id]
                player = sound_data['player']
                
                # Stop se sta già suonando
                if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    player.stop()
                
                # Riposiziona all'inizio e riproduci
                player.setPosition(0)
                player.play()
                
            else:
                # WINDOWS/MACOS: Usa QSoundEffect
                effect = self.sounds[sound_id]
                
                # Stop se sta già suonando
                if effect.isPlaying():
                    effect.stop()
                
                # Riproduci
                effect.play()
                
        except Exception as e:
            print(f"⚠️ Error playing sound {sound_id}: {e}")
    
    def cleanup(self):
        """
         Pulizia corretta delle risorse audio
        Importante su Linux per evitare memory leak
        """
        if not AUDIO_AVAILABLE:
            return
        
        try:
            if self.use_media_player:
                # Ferma e pulisci tutti i player
                for sound_id, sound_data in self.sounds.items():
                    player = sound_data['player']
                    if player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                        player.stop()
                    player.setSource(QUrl())  # Rilascia il file
            else:
                # Ferma tutti i sound effects
                for sound_id, effect in self.sounds.items():
                    if effect.isPlaying():
                        effect.stop()
            
            
            
        except Exception as e:
            print(f"⚠️ Error during audio cleanup: {e}")
    
    def __del__(self):
        """Distruttore: pulisci le risorse quando l'oggetto viene distrutto"""
        self.cleanup()
