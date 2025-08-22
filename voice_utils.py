# voice_utils.py

import speech_recognition as sr
import pyttsx3
import time # Pour une petite pause optionnelle si besoin

_tts_engine_global = None # Variable globale pour le moteur TTS

def initialiser_tts_engine(langue_cible='fr'):
    """
    Initialise le moteur Text-to-Speech (pyttsx3) une seule fois.
    Tente de configurer une voix française.
    """
    global _tts_engine_global
    if _tts_engine_global is not None and _tts_engine_global != "ERROR": # Déjà initialisé avec succès
        return _tts_engine_global
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        selected_voice_id = None

        # Tentative plus robuste pour trouver une voix française
        for voice in voices:
            # 1. Vérifier la propriété 'languages' si elle existe et contient 'fr'
            if hasattr(voice, 'languages') and voice.languages:
                if any(lang_code.lower().startswith(langue_cible) for lang_code in voice.languages):
                    selected_voice_id = voice.id
                    break
            # 2. Vérifier le nom ou l'ID de la voix pour des indicateurs français
            if langue_cible in voice.name.lower() or \
               f'_{langue_cible}' in voice.id.lower() or \
               f'-{langue_cible}' in voice.id.lower():
                selected_voice_id = voice.id
                break
        
        if selected_voice_id:
            engine.setProperty('voice', selected_voice_id)
            print(f"INFO: Voix TTS sélectionnée: {selected_voice_id}")
        else:
            print(f"AVERTISSEMENT: Aucune voix spécifiquement française trouvée. Utilisation de la voix système par défaut.")
            # Sur certains systèmes, définir la langue peut aider, mais ce n'est pas standardisé
            try:
                engine.setProperty('lang', langue_cible)
            except:
                pass 

        # Ajuster légèrement le débit pour une meilleure clarté (optionnel)
        rate = engine.getProperty('rate')
        engine.setProperty('rate', rate - 20) # Réduire un peu la vitesse

        _tts_engine_global = engine
        print("INFO: Moteur TTS initialisé avec succès.")
        return engine
    except Exception as e:
        print(f"ERREUR CRITIQUE: Impossible d'initialiser le moteur pyttsx3: {e}")
        print("INFO: La sortie vocale sera désactivée. Vérifiez vos pilotes audio et les dépendances de pyttsx3 (espeak, nsss, sapi5).")
        _tts_engine_global = "ERROR" # Marqueur pour indiquer l'échec
        return None


def parler(texte: str):
    """
    Convertit le texte en parole et le joue en utilisant le moteur TTS initialisé.
    Affiche également le texte dans la console.
    """
    global _tts_engine_global
    
    if not texte:
        # print("DEBUG (parler): Aucun texte fourni.")
        return

    print(f"🤖 Assistant (dit): {texte}") # Toujours imprimer pour le log / fallback

    if _tts_engine_global is None: # Si pas encore initialisé
        initialiser_tts_engine()
    
    if _tts_engine_global == "ERROR" or _tts_engine_global is None:
        # print("DEBUG (parler): Moteur TTS non disponible, affichage texte uniquement.")
        return # Le moteur n'a pas pu être initialisé

    try:
        _tts_engine_global.say(texte)
        _tts_engine_global.runAndWait()
    except Exception as e:
        print(f"ERREUR (parler): Échec de la synthèse vocale pour '{texte[:50]}...': {e}")


def ecouter_et_transcrire(langue_stt="fr-FR", timeout_ecoute=7, limite_phrase=10, tentatives_max=1):
    """
    Écoute le microphone, transcrit la parole en texte.
    Peut faire plusieurs tentatives si la reconnaissance échoue.
    """
    r = sr.Recognizer()
    tentative_actuelle = 0

    while tentative_actuelle < tentatives_max:
        tentative_actuelle += 1
        with sr.Microphone() as source:
            parler_interne = "Dites quelque chose..." if tentative_actuelle == 1 else "Veuillez réessayer de parler..."
            print(f"\n🎤 {parler_interne} (timeout: {timeout_ecoute}s, limite phrase: {limite_phrase}s)")
            # parler(parler_interne) # On peut aussi le dire à voix haute

            try:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout_ecoute, phrase_time_limit=limite_phrase)
            except sr.WaitTimeoutError:
                message_erreur = "Aucune parole détectée dans le temps imparti."
                print(message_erreur)
                if tentative_actuelle < tentatives_max:
                    parler(message_erreur + " Essayons encore.")
                    time.sleep(0.5) # Petite pause avant de réessayer
                    continue
                else:
                    parler(message_erreur)
                    return None
            except Exception as e:
                message_erreur = f"Erreur pendant l'écoute: {e}"
                print(message_erreur)
                parler("Oups, un problème est survenu avec le microphone.")
                return None

        try:
            # print("Transcription en cours...") # Peut être un peu verbeux si parlé
            texte_transcrit = r.recognize_google(audio, language=langue_stt)
            print(f"👤 Vous (transcrit): {texte_transcrit}")
            return texte_transcrit
        except sr.UnknownValueError:
            message_erreur = "Je n'ai pas réussi à comprendre ce que vous avez dit."
            print(message_erreur)
            if tentative_actuelle < tentatives_max:
                parler(message_erreur + " Pouvez-vous répéter ?")
                time.sleep(0.5)
                continue
            else:
                parler(message_erreur)
                return None
        except sr.RequestError as e:
            message_erreur = f"Erreur de service de reconnaissance vocale Google ; {e}"
            print(message_erreur)
            parler("Le service de reconnaissance vocale semble indisponible pour le moment.")
            return None # Erreur fatale pour cette tentative
        except Exception as e:
            message_erreur = f"Une erreur inattendue est survenue pendant la transcription: {e}"
            print(message_erreur)
            parler("Une erreur s'est produite lors de la transcription.")
            return None
    return None # Si toutes les tentatives échouent