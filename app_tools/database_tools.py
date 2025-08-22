# db_tools.py
# Fichier contenant les outils pour interagir avec la base de données Flooz.
# La structure sépare la logique métier (fonctions préfixées par _) des outils exposés à l'agent (@tool).

from langchain_core.tools import tool
from typing import Optional, List, Tuple, Dict, Any
from settings import db_connector # Assurez-vous que votre connecteur est bien importé
from datetime import datetime, timedelta


def _get_date_clause_and_params(start_date: Optional[str], end_date: Optional[str]) -> Tuple[str, List[Any]]:
    """Crée une clause WHERE pour une plage de dates et retourne les paramètres."""
    conditions = []
    params = []

    if not start_date and not end_date:
        # Par défaut, la journée en cours
        today = datetime.now()
        start_date = today.strftime("%Y-%m-%d 00:00:00")
        end_date = today.strftime("%Y-%m-%d 23:59:59")
    
    if start_date:
        conditions.append("created_at >= %s")
        params.append(start_date)
    
    if end_date:
        # Assurer que la date de fin inclut toute la journée
        if len(end_date) == 10: # Format 'YYYY-MM-DD'
            end_date += " 23:59:59"
        conditions.append("created_at <= %s")
        params.append(end_date)
        
    return " AND ".join(conditions), params

def _format_full_transaction_details(transaction: Dict[str, Any]) -> str:
    """Met en forme les détails complets d'une seule transaction pour l'affichage."""
    if not transaction:
        return "Transaction non trouvée."
    
    status_map = {True: "Succès", False: "Échec"}
    notif_map = {True: "Reçue", False: "Non reçue"}

    details = [
        f"Détails de la Transaction (ID interne: {transaction.get('id')})",
        f"  - Transaction ID: {transaction.get('transaction_id')}",
        f"  - Numéro de transaction: {transaction.get('number')}",
        f"  - Référence Opérateur: {transaction.get('reference_id', 'N/A')}",
        f"  - Montant: {transaction.get('paid_transaction_amount')} {transaction.get('currency_id')}",
        f"  - Numéro de téléphone: {transaction.get('phone_number')}",
        f"  - Statut Paiement: {status_map.get(transaction.get('payment_status'), 'Inconnu/En attente')}",
        f"  - Notification Wallet: {notif_map.get(transaction.get('wallet_notification_received'), 'N/A')}",
        f"  - Date Création: {transaction.get('created_at')}",
        f"  - Dernière MàJ: {transaction.get('updated_at')}"
    ]
    return "\n".join(details)



@tool
def get_transaction_details(
    transaction_id: Optional[str] = None,
    transaction_number: Optional[str] = None,
    reference_id: Optional[str] = None
) -> str:
    """
    Récupère les détails d'une transaction SEULEMENT si l'utilisateur spécifie EXPLICITEMENT le type d'identifiant ('transaction_id', 'number', ou 'reference_id').
    NE PAS utiliser cet outil si l'utilisateur dit juste 'référence' ou 'ID'. Dans ce cas, utiliser 'find_transaction_by_any_reference'.
    """
    if not any([transaction_id, transaction_number, reference_id]):
        return "Erreur de l'outil: au moins un identifiant (transaction_id, transaction_number, ou reference_id) est requis."

    query = "SELECT * FROM flooz_baskets WHERE "
    conditions = []
    params = []

    if transaction_id:
        conditions.append("transaction_id = %s")
        params.append(transaction_id)
    if transaction_number:
        conditions.append("number = %s")
        params.append(transaction_number)
    if reference_id:
        conditions.append("reference_id = %s")
        params.append(reference_id)
    
    query += " OR ".join(conditions) + " LIMIT 1;"

    try:
        transaction_data = db_connector.fetch_one(query, tuple(params))
        return _format_full_transaction_details(transaction_data)
    except Exception as e:
        return f"Une erreur est survenue lors de la recherche de la transaction: {e}"

@tool
def find_transactions_by_criteria(
    payment_status: Optional[bool] = None,
    phone_number: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    wallet_notification_received: Optional[bool] = None,
    limit: int = 5
) -> str:
    """
    Recherche et affiche une LISTE de transactions individuelles basées sur des critères de FILTRAGE précis.
    Très utile pour des questions comme 'liste les 5 dernières transactions échouées' ou 'trouve les transactions pour le numéro X hier'.
    NE PAS utiliser cet outil pour obtenir des statistiques, des comptes ou des totaux.
    """
    query = "SELECT transaction_id, number, paid_transaction_amount, payment_status, wallet_notification_received, created_at, phone_number FROM flooz_baskets WHERE 1=1"
    params = []

    if payment_status is not None:
        query += " AND payment_status = %s"
        params.append(payment_status)
    if phone_number:
        query += " AND phone_number = %s"
        params.append(phone_number)
    if wallet_notification_received is not None:
        query += " AND wallet_notification_received = %s"
        params.append(wallet_notification_received)
    
    date_clause, date_params = _get_date_clause_and_params(start_date, end_date)
    if date_clause:
        query += f" AND {date_clause}"
        params.extend(date_params)

    query += f" ORDER BY created_at DESC LIMIT %s;"
    params.append(limit)

    try:
        transactions = db_connector.fetch_all(query, tuple(params))
        if not transactions:
            return "Aucune transaction correspondante trouvée pour ces critères."

        summary_list = ["Transactions trouvées:"]
        for tx in transactions:
            status_str = "Succès" if tx.get('payment_status') else "Échec"
            summary_list.append(
                f"- ID: {tx.get('transaction_id')}, Num: {tx.get('number')}, Date: {tx.get('created_at')}, "
                f"Statut: {status_str}, Tél: {tx.get('phone_number')}"
            )
        return "\n".join(summary_list)
    except Exception as e:
        return f"Une erreur est survenue lors de la recherche: {e}"

@tool
def get_transaction_summary(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    Calcule et retourne des statistiques globales : le nombre TOTAL de transactions et le montant TOTAL pour une période donnée (par défaut, aujourd'hui).
    Utilise cet outil pour des questions comme 'quel est le volume total de la semaine ?' ou 'combien de transactions aujourd'hui ?'.
    """
    date_clause, params = _get_date_clause_and_params(start_date, end_date)
    query = f"SELECT COUNT(*) as total_count, SUM(paid_transaction_amount) as total_amount FROM flooz_baskets WHERE {date_clause}"
    
    try:
        data = db_connector.fetch_one(query, tuple(params))
        count = data.get('total_count', 0)
        amount = data.get('total_amount', 0.0) or 0.0
        return f"Résumé pour la période: {count} transactions pour un montant total de {amount:.2f}."
    except Exception as e:
        return f"Erreur lors du calcul du résumé: {e}"

@tool
def get_pending_transactions_count(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    Compte le nombre de transactions dont le statut de paiement est indéterminé (NULL) sur une période donnée (par défaut, aujourd'hui).
    Très utile pour des questions comme 'combien de transactions sont en attente ?' ou 'y a-t-il des transactions bloquées ?'.
    """
    date_clause, params = _get_date_clause_and_params(start_date, end_date)
    query = f"SELECT COUNT(*) as null_count FROM flooz_baskets WHERE payment_status IS NULL AND {date_clause}"

    try:
        data = db_connector.fetch_one(query, tuple(params))
        return f"Nombre de transactions en attente (statut NULL): {data.get('null_count', 0)}."
    except Exception as e:
        return f"Erreur lors du comptage des transactions en attente: {e}"

@tool
def get_top_active_phone_numbers(limit: int = 5, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    Analyse et retourne un classement des numéros de téléphone les plus actifs (ceux avec le plus de transactions) sur une période donnée.
    Utilise cet outil pour des questions comme 'quels sont les numéros les plus récurrents ?' ou 'top 5 des clients les plus actifs cette semaine'.
    """
    date_clause, params = _get_date_clause_and_params(start_date, end_date)
    query = f"""
        SELECT phone_number, COUNT(*) as transaction_count FROM flooz_baskets
        WHERE {date_clause} AND phone_number IS NOT NULL
        GROUP BY phone_number 
        ORDER BY transaction_count DESC 
        LIMIT %s
    """
    params.append(limit)

    try:
        data = db_connector.fetch_all(query, tuple(params))
        if not data:
            return "Aucune activité de numéro de téléphone trouvée pour cette période."
        
        results = [f"Classement des {limit} numéros les plus actifs:"]
        for row in data:
            results.append(f"  - {row['phone_number']}: {row['transaction_count']} transactions")
        return "\n".join(results)
    except Exception as e:
        return f"Erreur lors de l'analyse des numéros récurrents: {e}"
        
@tool
def get_wallet_notification_stats(start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """
    Fournit des statistiques sur les notifications wallet (reçues vs non reçues) sur une période donnée.
    Utilise cet outil pour répondre à des questions sur la santé des notifications wallet.
    """
    date_clause, params = _get_date_clause_and_params(start_date, end_date)
    query = f"""
        SELECT 
            SUM(CASE WHEN wallet_notification_received = TRUE THEN 1 ELSE 0 END) as received_count,
            SUM(CASE WHEN wallet_notification_received = FALSE THEN 1 ELSE 0 END) as not_received_count
        FROM flooz_baskets WHERE {date_clause}
    """
    try:
        data = db_connector.fetch_one(query, tuple(params))
        received = data.get('received_count', 0) or 0
        not_received = data.get('not_received_count', 0) or 0
        return f"Statistiques des notifications wallet: Reçues: {received}, Non reçues: {not_received}."
    except Exception as e:
        return f"Erreur lors du calcul des stats de notifications: {e}"
    



 #outil passe partout

@tool
def find_transaction_by_any_reference(reference_value: str) -> str:
    """
    Recherche une transaction en utilisant une valeur de référence générique.
    Cet outil est le MEILLEUR CHOIX lorsque l'utilisateur fournit une chaîne de caractères et la nomme 'référence', 'ID', 'identifiant' ou un terme similaire, sans préciser s'il s'agit d'un 'transaction_id', d'un 'number' ou d'un 'reference_id'.
    Il cherche la valeur fournie dans les colonnes 'transaction_id', 'number', et 'reference_id' simultanément.
    Il retourne les détails complets de la transaction si une correspondance unique est trouvée.
    """
    if not reference_value:
        return "Erreur de l'outil: une valeur de référence doit être fournie."

    # La requête SQL va chercher dans les 3 colonnes avec des OR
    query = """
        SELECT * FROM flooz_baskets 
        WHERE transaction_id = %s 
           OR number = %s 
           OR reference_id = %s
        LIMIT 2;  -- On met une limite à 2 pour détecter les ambiguïtés
    """
    params = (reference_value, reference_value, reference_value)

    try:
        transactions = db_connector.fetch_all(query, params)

        if not transactions:
            return f"Résultat final de la recherche : Aucune transaction trouvée pour la référence '{reference_value}'."
        
        if len(transactions) > 1:
            # Cas où la référence est ambiguë (ex: un reference_id non unique)
            ids_found = [tx.get('transaction_id') for tx in transactions]
            return (f"La référence '{reference_value}' est ambiguë et correspond à plusieurs transactions "
                    f"(IDs: {', '.join(ids_found)}). Veuillez utiliser un identifiant plus spécifique.")

        # Si on trouve exactement une transaction, on affiche ses détails complets
        # On réutilise la fonction de formatage que vous avez déjà !
        return _format_full_transaction_details(transactions[0])

    except Exception as e:
        return f"Une erreur est survenue lors de la recherche par référence : {e}"