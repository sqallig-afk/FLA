"""
Service LLM — UN seul appel Claude qui analyse le texte libre + documents
et retourne TOUS les champs FLA remplis intelligemment.
Fallback templates si pas de clé API.
"""

import os
import json
import base64

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


def get_client():
    """Retourne un client Anthropic si la clé est disponible."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not HAS_ANTHROPIC:
        return None
    return anthropic.Anthropic(api_key=api_key)


def is_available() -> bool:
    """Vérifie si le service LLM est disponible."""
    return get_client() is not None


# ─────────────────────────────────────────────────────────────
# PROMPT PRINCIPAL — un seul appel, Claude remplit TOUT
# ─────────────────────────────────────────────────────────────

FULL_FLA_PROMPT = """Tu es un assistant interne du laboratoire de biologie clinique (CHR Citadelle, Liège) du Dr. Sqalli.
Tu reçois un texte libre (en vrac, abrégé, avec fautes, argot) et/ou des infos extraites d'un document (devis, capture d'écran).

Ton rôle : INTERPRÉTER intelligemment ce texte et remplir TOUS les champs d'une Fiche de Lancement d'Achat (FLA).

RÈGLES CRITIQUES :
- INTERPRÈTE le texte : "centre du pérou pour infirmières" → "Centre de prélèvement pour le personnel infirmier"
- CHERCHE AGRESSIVEMENT les prix dans tous les formats : "12500", "12.500€", "devis à 15k", "±3000", etc.
- Marque/modèle : ne recopie QUE si mentionnés explicitement. Sinon → "selon devis joint" ou "à confirmer"
- Codes INAMI : ne JAMAIS inventer → "Sans objet"
- Service demandeur = toujours "Laboratoire de biologie clinique"
- Site par défaut = "CHR Citadelle – laboratoire de biologie clinique"
- Local par défaut = "Local existant (laboratoire) – pas de local supplémentaire"
- Quantité = 1 sauf si précisé
- Date = "Dès validation" sauf si précisé
- Montant si absent = "Selon devis joint"

RAISON DE L'ACHAT — choisis UNE SEULE valeur EXACTE parmi :
- "Remplacement /éch standard matériel vétuste ou défectueux"
- "Remplacement /éch standard matériel cassé par une mauvaise manipulation"
- "Remplacement matériel perdu"
- "Extension du parc existant / augmentation de l'activité existante"
- "Amélioration de l'existant (qualité, sécurité, innovation, etc.)"
- "Nouvelle activité"
- "Autre : spécifier dans la case suivante"

CATÉGORIE — choisis UNE SEULE valeur EXACTE parmi :
"LABORATOIRE", "MEDICAL", "INFORMATIQUE MEDICAL", "INFORMATIQUE HORS MEDICAL", "MOBILIER", "ELECTRO/AUDIOVISUEL/TELEPHONIE", "FOURNITURES BUREAU", "PHARMACIE", "SERVICES GENERAUX", "TECHNIQUE ET INFRASTRUCTURE", "ALIMENTATION/HORECA", "FLEET", "GESTION DES DECHETS", "HYGIENE/PROTECTION INDIVIDUELLE (EPI)", "NETTOYAGE/LINGERIE/TENUES"

CONSOMMABLES — choisis UN parmi : "Pas de consommables", "Consommables non-médicaux", "Consommables médicaux stériles", "Consommables médicaux non-stériles", "Consommables médicaux stériles ET non-stériles", "Ne sais pas"

MAINTENANCE — choisis UN parmi : "Omnium", "Semi-omnium", "Préventive", "Interne à l'institution", "Pas de maintenance", "Ne sais pas"

IT — choisis UN parmi : "Aucune intervention de l'IT", "Equipement IT nécessaire (PC, serveur, etc)", "Connexion nécessaire (Wifi, câble)", "Intégration au système IT nécessaire (DPI, etc)", "Plusieurs interventions de l'IT (équipement, connexions, intégrations)", "Ne sais pas"

MOTIVATION : rédige 3-5 phrases professionnelles sur pourquoi c'est ESSENTIEL (qualité, sécurité, continuité, délais, patients). Intègre TOUTES les infos du texte libre intelligemment.
Si remplacement sans cause précise → "remplacement d'un matériel vétuste/défectueux (circonstances à confirmer)".

RENTABILITÉ : 3-5 phrases sur la justification financière (INAMI, efficience, activité externalisée). Ne pas inventer de codes INAMI.

Réponds UNIQUEMENT avec un JSON valide (sans ```json) :
{
  "objet": "",
  "categorie": "",
  "raison": "",
  "motivation": "",
  "rentabilite": "",
  "is_remplacement": false,
  "remplacement_info": "Sans objet",
  "reprise": "Non",
  "site": "CHR Citadelle – laboratoire de biologie clinique",
  "local": "Local existant (laboratoire) – pas de local supplémentaire",
  "quantite": 1,
  "prix_unitaire": "",
  "montant_total": "Selon devis joint",
  "date_mise_en_service": "Dès validation",
  "fournisseurs": "",
  "compatibilite": "Sans objet",
  "consommables": "",
  "estimation_consommables": "À confirmer",
  "maintenance": "",
  "estimation_maintenance": "À confirmer",
  "subside": "Non",
  "nb_patients": "Sans objet",
  "code_inami": "Sans objet",
  "montant_inami": "Sans objet",
  "pct_hopital_inami": "Sans objet",
  "ressources_humaines": "Sans objet",
  "categories_rh": "Sans objet",
  "travaux": "Non",
  "estimation_travaux": "",
  "it": "",
  "estimation_it": "",
  "rgpd": "Non",
  "sipp": "Non",
  "hygiene": "Non",
  "autres_parties": "",
  "formation": "Non",
  "tests": "Non"
}"""


def analyze_request(user_text: str, extracted_doc_info: str = "") -> dict:
    """
    UN seul appel Claude : analyse le texte libre + infos documents
    et retourne TOUS les champs FLA remplis.
    """
    client = get_client()
    if not client:
        return {}

    message = user_text
    if extracted_doc_info:
        message += f"\n\nInformations extraites du document joint :\n{extracted_doc_info}"

    # Essayer plusieurs modèles avec retry
    import time
    models = ["claude-sonnet-4-20250514", "claude-opus-4-20250514"]
    last_error = None

    for model in models:
        for attempt in range(3):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=2500,
                    system=FULL_FLA_PROMPT,
                    messages=[{"role": "user", "content": message}],
                )
                raw = response.content[0].text.strip()
                # Nettoyer si Claude a mis des backticks
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                    raw = raw.rsplit("```", 1)[0]
                return json.loads(raw)
            except Exception as e:
                last_error = e
                if "overloaded" in str(e).lower() or "529" in str(e):
                    time.sleep(2 * (attempt + 1))
                    continue
                break  # Autre erreur, essayer le modèle suivant
        # Si on arrive ici, ce modèle a échoué, on essaie le suivant

    return {"_error": str(last_error)}


# ─────────────────────────────────────────────────────────────
# FALLBACK TEMPLATES (si pas de clé API)
# ─────────────────────────────────────────────────────────────

MOTIVATION_TEMPLATES = {
    "default": (
        "L'acquisition de {objet} est essentielle pour garantir la continuité et la qualité "
        "des activités du laboratoire de biologie clinique. {contexte_phrase}"
        "Ce matériel contribue directement à la fiabilité des résultats, "
        "à la sécurité des processus analytiques et au maintien des délais de rendu "
        "attendus par les cliniciens et les patients."
    ),
    "remplacement": (
        "Le remplacement de ce matériel est indispensable pour assurer la continuité "
        "des activités du laboratoire de biologie clinique. {contexte_phrase}"
        "L'équipement actuel, vétuste ou défectueux, compromet la fiabilité des résultats "
        "et la sécurité des processus analytiques (circonstances précises à confirmer)."
    ),
}

RENTABILITE_TEMPLATES = {
    "default": (
        "Les analyses réalisées grâce à ce matériel font l'objet d'une facturation "
        "au patient via les codes INAMI applicables. L'investissement contribue "
        "à l'efficience du laboratoire (optimisation des flux, réduction des délais de rendu) "
        "et au maintien de l'activité d'analyses externalisées, source de revenus pour l'institution."
    ),
}


def generate_fallback(objet: str, contexte: str) -> dict:
    """Génère un dict FLA minimal via templates (sans API)."""
    is_remp = any(w in (objet + " " + contexte).lower() for w in ["remplacer", "remplacement", "ancien", "vétuste", "casse"])
    ctx = f"{contexte}. " if contexte.strip() else ""
    key = "remplacement" if is_remp else "default"

    return {
        "objet": objet,
        "motivation": MOTIVATION_TEMPLATES[key].format(objet=objet, contexte_phrase=ctx),
        "rentabilite": RENTABILITE_TEMPLATES["default"],
        "is_remplacement": is_remp,
    }
