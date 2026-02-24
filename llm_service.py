"""
Service LLM hybride - Claude API + fallback templates.
Génère les textes narratifs (motivation, rentabilité) et extrait les infos des documents.
Fonction principale : analyze_full_request() — analyse le texte libre et déduit TOUS les champs FLA.
"""

import os
import json
import base64
from pathlib import Path

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


# --- Extraction des faits depuis texte libre ---

EXTRACT_FACTS_PROMPT = """Tu es un assistant du laboratoire de biologie clinique du CHR Citadelle (Liège).

L'utilisateur décrit en vrac ce qu'il veut acheter. Ton rôle est d'extraire les FAITS mentionnés.
N'invente RIEN. Si une info n'est pas mentionnée, mets une chaîne vide "".
Ne mets JAMAIS de valeurs par défaut — laisse vide et le système s'en chargera.
Marque/modèle : ne recopie QUE si l'utilisateur les mentionne explicitement.

Réponds UNIQUEMENT avec un JSON valide (sans ```json ni commentaires) :
{
  "objet": "description de ce que l'utilisateur veut acheter",
  "contexte": "le contexte / justification / raison mentionné par l'utilisateur",
  "is_remplacement": true/false,
  "remplacement_info": "marque/modèle/année de l'ancien matériel si mentionné, sinon vide",
  "quantite": nombre ou null,
  "prix_unitaire": "prix unitaire si mentionné",
  "montant_total": "montant total si mentionné",
  "fournisseurs": "fournisseurs si mentionnés",
  "date_souhaitee": "date si mentionnée",
  "site": "site si différent du CHR Citadelle labo",
  "compatibilite": "info de compatibilité si mentionnée",
  "nom_demandeur": "nom du demandeur si mentionné"
}"""


def extract_facts_from_text(user_text: str, extracted_doc_info: str = "") -> dict:
    """
    Extrait les faits bruts du texte libre de l'utilisateur.
    Ne déduit PAS les champs de la FLA — c'est le moteur de règles qui s'en charge.
    """
    client = get_client()
    if not client:
        return {}

    message = user_text
    if extracted_doc_info:
        message += f"\n\nInformations extraites du document joint :\n{extracted_doc_info}"

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=800,
            system=EXTRACT_FACTS_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1]
            raw = raw.rsplit("```", 1)[0]
        return json.loads(raw)
    except Exception:
        return {}


# --- Templates fallback ---

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
    "nouvelle_activite": (
        "L'acquisition de {objet} permettra au laboratoire de biologie clinique "
        "de développer une nouvelle activité, répondant à un besoin clinique identifié. "
        "{contexte_phrase}"
        "Cette offre renforcera le positionnement du CHR Citadelle et contribuera "
        "à améliorer la prise en charge des patients."
    ),
    "extension": (
        "L'acquisition de {objet} est nécessaire pour répondre à l'augmentation "
        "de l'activité du laboratoire de biologie clinique. {contexte_phrase}"
        "Le parc actuel ne suffit plus à absorber le volume d'analyses, "
        "impactant les délais de rendu et la qualité du service."
    ),
    "amelioration": (
        "L'acquisition de {objet} vise à améliorer la qualité et/ou la sécurité "
        "des processus du laboratoire de biologie clinique. {contexte_phrase}"
        "Cette amélioration contribuera à l'optimisation des performances analytiques "
        "et au respect des normes en vigueur."
    ),
}

RENTABILITE_TEMPLATES = {
    "default": (
        "Les analyses réalisées grâce à ce matériel font l'objet d'une facturation "
        "au patient via les codes INAMI applicables. L'investissement contribue "
        "à l'efficience du laboratoire (optimisation des flux, réduction des délais de rendu) "
        "et au maintien de l'activité d'analyses externalisées, source de revenus pour l'institution."
    ),
    "consommable": (
        "Les consommables sont directement intégrés dans le coût des analyses facturées "
        "via les codes INAMI. Leur approvisionnement est indispensable à la continuité "
        "de l'activité analytique et donc aux recettes associées."
    ),
    "mobilier": (
        "Cet achat relève de l'aménagement nécessaire au bon fonctionnement du service. "
        "Il contribue indirectement à l'efficience du laboratoire en optimisant "
        "l'organisation et les conditions de travail du personnel."
    ),
    "logiciel": (
        "Ce logiciel contribue à l'efficience du laboratoire par l'optimisation "
        "des processus, la réduction des erreurs et l'amélioration de la traçabilité. "
        "L'investissement se justifie par les gains en productivité et en qualité "
        "qui en découlent."
    ),
}


def _get_motivation_template_key(raison: str, objet: str) -> str:
    """Détermine le template de motivation à utiliser."""
    raison_lower = raison.lower()
    if "remplacement" in raison_lower:
        return "remplacement"
    if "nouvelle activité" in raison_lower:
        return "nouvelle_activite"
    if "extension" in raison_lower or "augmentation" in raison_lower:
        return "extension"
    if "amélioration" in raison_lower:
        return "amelioration"
    return "default"


def _get_rentabilite_template_key(objet: str, categorie: str) -> str:
    """Détermine le template de rentabilité à utiliser."""
    objet_lower = objet.lower()
    if any(w in objet_lower for w in ["logiciel", "software", "licence"]):
        return "logiciel"
    if any(w in objet_lower for w in ["armoire", "bureau", "chaise", "meuble", "chariot"]):
        return "mobilier"
    if any(w in objet_lower for w in ["tube", "réactif", "kit", "consommable", "aiguille"]):
        return "consommable"
    return "default"


def generate_motivation_fallback(objet: str, contexte: str, raison: str) -> str:
    """Génère la motivation via template."""
    key = _get_motivation_template_key(raison, objet)
    template = MOTIVATION_TEMPLATES[key]
    contexte_phrase = f"{contexte}. " if contexte.strip() else ""
    return template.format(objet=objet, contexte_phrase=contexte_phrase)


def generate_rentabilite_fallback(objet: str, categorie: str) -> str:
    """Génère la rentabilité via template."""
    key = _get_rentabilite_template_key(objet, categorie)
    return RENTABILITE_TEMPLATES[key]


def generate_motivation_llm(objet: str, contexte: str, raison: str, is_remplacement: bool) -> str:
    """Génère la motivation via Claude API."""
    client = get_client()
    if not client:
        return generate_motivation_fallback(objet, contexte, raison)

    remplacement_note = ""
    if is_remplacement:
        remplacement_note = (
            "\nC'est un remplacement. Si la cause précise n'est pas donnée, "
            "indique 'remplacement d'un matériel vétuste/défectueux (circonstances à confirmer)' "
            "plutôt que d'inventer un événement précis."
        )

    prompt = f"""Tu es un assistant du laboratoire de biologie clinique du CHR Citadelle (Liège).
Rédige la motivation d'achat pour une fiche de lancement d'achat (FLA).

La motivation doit expliquer en quoi cet achat est ESSENTIEL pour l'activité de l'hôpital.
Elle doit être courte (3-5 phrases), professionnelle, et mettre en avant :
- L'impact sur la qualité des résultats
- La sécurité des processus
- La continuité d'activité / délais de rendu
- L'intérêt clinique/patient
- Si pertinent, le soutien de l'activité externe

Objet : {objet}
Contexte : {contexte if contexte else 'Non précisé'}
Raison de l'achat : {raison}
{remplacement_note}

Réponds UNIQUEMENT avec le texte de la motivation, sans titre ni préambule."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_rentabilite_llm(objet: str, contexte: str, categorie: str, montant: str) -> str:
    """Génère la rentabilité via Claude API."""
    client = get_client()
    if not client:
        return generate_rentabilite_fallback(objet, categorie)

    prompt = f"""Tu es un assistant du laboratoire de biologie clinique du CHR Citadelle (Liège).
Rédige les informations de rentabilité pour une fiche de lancement d'achat (FLA).

La rentabilité doit expliquer comment l'achat/dépense est justifié financièrement :
- Refacturation au patient (codes INAMI si applicable)
- Optimisation des coûts
- Efficience du personnel
- Maintien/développement de l'activité d'analyses externalisées

Objet : {objet}
Catégorie : {categorie}
Contexte : {contexte if contexte else 'Non précisé'}
Montant estimé : {montant if montant else 'Non précisé'}

Réponds UNIQUEMENT avec le texte de la rentabilité (3-5 phrases), sans titre ni préambule.
Ne mentionne PAS de codes INAMI spécifiques si tu ne les connais pas."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_motivation(objet: str, contexte: str, raison: str, is_remplacement: bool) -> str:
    """Point d'entrée : génère la motivation (LLM si dispo, sinon template)."""
    if is_available():
        try:
            return generate_motivation_llm(objet, contexte, raison, is_remplacement)
        except Exception:
            pass
    return generate_motivation_fallback(objet, contexte, raison)


def generate_rentabilite(objet: str, contexte: str, categorie: str, montant: str) -> str:
    """Point d'entrée : génère la rentabilité (LLM si dispo, sinon template)."""
    if is_available():
        try:
            return generate_rentabilite_llm(objet, contexte, categorie, montant)
        except Exception:
            pass
    return generate_rentabilite_fallback(objet, categorie)
