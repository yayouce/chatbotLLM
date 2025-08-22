

import re
import json
from datetime import datetime

# --- Fonctions utilitaires---
def _extract_context_id(text: str) -> str | None:
    """Tente d'extraire n'importe quel ID de transaction probable d'une chaîne de texte."""
    if not isinstance(text, str): return None
    
    # Regex améliorée qui cherche des formats spécifiques dans un ordre de priorité
    # Longs nombres (souvent des transaction_id)
    match = re.search(r'\b(\d{14,})\b', text)
    if match: return match.group(1)
    
    #  Tokens  (commençant par MP)
    match = re.search(r'(MP\d{6}\.[A-Z0-9\.]+)', text)
    if match: return match.group(1)

    #  Tokens alphanumériques longs (souvent des tokens de notification ou des order_id)
    match = re.search(r'([a-zA-Z0-9-]{12,})', text)
    if match and "token" in text.lower(): # On s'assure que c'est bien un token
        return match.group(1)

    #  Autres formats
    match = re.search(r'(CF[A-Z0-9]+|cos-[\w-]+)', text)
    if match: return match.group(1)
    
    return None

def _extract_semantic_status(text: str) -> str | None:
    lower_text = text.lower()
    if any(k in lower_text for k in ["fail", "error", "exception", "unpermitted", "404 not found", "rollback"]):
        return "FAILURE"
    if any(k in lower_text for k in ["success", "processed successfully", "paiement effectue avec succes", "completed 200 ok", "commit"]):
        return "SUCCESS"
    return None

def _extract_ip_address(text: str) -> str | None:
    match = re.search(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text)
    return match.group(0) if match else None

# --- Dictionnaire de Patterns Regex (Enrichi) ---
PATTERNS = {
    'request_start': re.compile(r'Started (?P<http_method>\w+) "(?P<http_path>.*?)" for (?P<ip_address>[\d\.]+)'),
    'processing': re.compile(r'Processing by (?P<controller_action>[\w:#]+) as (?P<format>\w+)'),
    'parameters': re.compile(r'Parameters: (?P<params_str>\{.*\})'),
    'completed': re.compile(r'Completed (?P<http_status>\d{3}.*?) in (?P<duration_total_ms>[\d\.]+)ms \(Views: .*? \| ActiveRecord: (?P<duration_activerecord_ms>[\d\.]+)ms\)'),
    'sql_query': re.compile(r'(?P<sql_model>[\w]+) (?P<sql_operation>Load|Create|Update|Exists)\s+\((?P<sql_duration_ms>[\d\.]+)ms\)\s+(?P<sql_query>(?:SELECT|INSERT|UPDATE).*)'),
    'ethon_call': re.compile(r'ETHON: performed EASY .* effective_url=(?P<external_url>https?://.*?) response_code=(?P<response_code>\d+)'),
    'redirected': re.compile(r'Redirected to (?P<redirect_url>https?://.*)'),
    ### NOUVEAUX PATTERNS ###
    'external_request': re.compile(r'GOING BODY (?P<external_service>[\w\s]+) PAYMENT REQUEST:'),
    'external_response': re.compile(r'RESPONSE (?P<external_service>[\w\s]+) GONE REQUEST: (?P<external_response_body>\{.*\})'),
}

def parse_log_line(line: str) -> dict | None:
    """
    Parse une ligne de log, extrait un maximum de métadonnées, et la classifie.
    """
    line = line.strip()
    if not line: return None
        
    clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
    data = {'raw_log': clean_line}
    
    # --- Étape 1: Extraction de la structure de base (corrigée) ---
    base_match = re.match(r'(?P<level_char>\w), \[(?P<timestamp_str>[^\]]+) #(?P<pid>\d+)\]\s+(?P<level>\w+)\s+--\s*:\s*(?P<message>.*)', clean_line)
    start_match = PATTERNS['request_start'].match(clean_line)
    
    if base_match:
        data.update(base_match.groupdict())
        message = data.get('message', '')
    elif start_match:
        data.update(start_match.groupdict())
        data['log_type'] = 'request_start'
        message = ""
    else:
        return None

    # --- Étape 2: Conversion du Timestamp (corrigée et robuste) ---
    ts_str = data.get('timestamp_str')
    if ts_str:
        # On nettoie le timestamp pour qu'il soit parsable
        ts_clean = ts_str.split(' +')[0].replace('T', ' ')
        try:
            # On essaie le format avec les microsecondes d'abord
            dt_object = datetime.strptime(ts_clean, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            try:
                # Sinon, on essaie sans les microsecondes
                dt_object = datetime.strptime(ts_clean, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                dt_object = None
        # On stocke l'objet datetime ET une version string ISO standard
        data['timestamp'] = dt_object
        data['timestamp_iso'] = dt_object.isoformat() if dt_object else None
    
    

    if 'log_type' not in data:
        for log_type, pattern in PATTERNS.items():
            match = pattern.match(message)
            if match:
                data['log_type'] = log_type
                data.update(match.groupdict())
                
                ### LOGIQUE SPÉCIFIQUE POUR LES NOUVEAUX PATTERNS ###
                if log_type == 'external_response':
                    data['external_call_type'] = 'RESPONSE'
                    try:
                        # On parse le JSON de la réponse pour extraire des champs clés
                        response_json = json.loads(data['external_response_body'])
                        data['external_session_id'] = response_json.get('id')
                        data['external_checkout_status'] = response_json.get('checkout_status')
                        data['external_payment_status'] = response_json.get('payment_status')
                    except json.JSONDecodeError:
                        pass # On ne fait rien si le JSON est mal formé
                
                elif log_type == 'external_request':
                    data['external_call_type'] = 'REQUEST'
                
                break
        else:
            data['log_type'] = 'generic_log'

   
    
    context_id= _extract_context_id(clean_line)
    if context_id:
        data['context_id']=context_id

    data['semantic_status'] = _extract_semantic_status(clean_line)
    if 'ip_address' not in data:
        data['ip_address'] = None 

    # Nettoyage des champs inutiles
    data.pop('timestamp_str', None)
    data.pop('level_char', None)
    data.pop('pid', None)
    data.pop('message', None)
    # On convertit l'objet datetime en string pour les métadonnées
    if 'timestamp' in data and data['timestamp']:
        data['timestamp'] = str(data['timestamp'])
    
    return data