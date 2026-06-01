AUDIO_VIDEO_TYPES = (
    ("Áudio e vídeo", "*.mp3 *.wav *.m4a *.ogg *.flac *.mp4 *.mkv *.webm *.avi"),
    ("Todos os arquivos", "*.*"),
)

QUALITY_CHOICES = (
    ("Rápida (menos RAM, mais erros)", "rapida"),
    ("Equilibrada (recomendado)", "equilibrada"),
    ("Alta qualidade (mais lento)", "alta"),
    ("Personalizado", "personalizado"),
)

LANGUAGE_CHOICES = ("pt", "en", "es", "fr", "de", "it", "auto")
