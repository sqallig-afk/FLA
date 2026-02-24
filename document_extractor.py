"""
Extraction d'informations depuis des documents uploadés (devis PDF, images).
Utilise Claude Vision si disponible, sinon retourne un dict vide.
"""

import base64
import io
import os

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False


EXTRACTION_PROMPT = """Tu es un assistant du laboratoire de biologie clinique du CHR Citadelle (Liège).
Analyse ce document (devis, fiche technique ou capture d'écran) et extrais les informations suivantes.

Retourne UNIQUEMENT un bloc structuré avec ces champs (laisse vide si non trouvé) :

MARQUE_MODELE: [marque et modèle du produit/équipement]
FOURNISSEUR: [nom du fournisseur]
PRIX_UNITAIRE_HT: [prix unitaire HT si mentionné]
PRIX_UNITAIRE_TVAC: [prix unitaire TVAC si mentionné]
MONTANT_TOTAL_HT: [montant total HT]
MONTANT_TOTAL_TVAC: [montant total TVAC]
QUANTITE: [quantité]
MAINTENANCE_MENTIONNEE: [Oui/Non - un contrat de maintenance est-il mentionné ?]
MONTANT_MAINTENANCE: [montant maintenance annuel si mentionné]
CONSOMMABLES_MENTIONNES: [Oui/Non - des consommables sont-ils mentionnés ?]
MONTANT_CONSOMMABLES: [montant consommables annuel si mentionné]
DESCRIPTION_OBJET: [description courte de l'objet principal du devis]

Ne mets PAS de commentaires, juste les valeurs. Si une info n'est pas trouvée, laisse la ligne vide après le ":"."""


def _parse_extraction_response(text: str) -> dict:
    """Parse la réponse structurée du LLM en dict."""
    result = {}
    key_mapping = {
        "MARQUE_MODELE": "marque_modele",
        "FOURNISSEUR": "fournisseur",
        "PRIX_UNITAIRE_HT": "prix_unitaire_ht",
        "PRIX_UNITAIRE_TVAC": "prix_unitaire_tvac",
        "MONTANT_TOTAL_HT": "montant_total_ht",
        "MONTANT_TOTAL_TVAC": "montant_total_tvac",
        "QUANTITE": "quantite",
        "MAINTENANCE_MENTIONNEE": "maintenance_mentionnee",
        "MONTANT_MAINTENANCE": "montant_maintenance",
        "CONSOMMABLES_MENTIONNES": "consommables_mentionnes",
        "MONTANT_CONSOMMABLES": "montant_consommables",
        "DESCRIPTION_OBJET": "description_objet",
    }

    for line in text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            key_part, _, value = line.partition(":")
            key_part = key_part.strip()
            value = value.strip()
            if key_part in key_mapping and value:
                result[key_mapping[key_part]] = value

    return result


def extract_from_image(image_bytes: bytes, mime_type: str = "image/png") -> dict:
    """Extrait les informations d'une image via Claude Vision."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not HAS_ANTHROPIC:
        return {}

    client = anthropic.Anthropic(api_key=api_key)
    b64_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": mime_type,
                                "data": b64_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
        )
        return _parse_extraction_response(response.content[0].text)
    except Exception:
        return {}


def extract_from_pdf(pdf_bytes: bytes) -> dict:
    """Extrait les informations d'un PDF.

    Tente d'abord l'extraction de texte avec PyPDF2, puis envoie au LLM.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or not HAS_ANTHROPIC:
        return {}

    # Extraire le texte du PDF
    pdf_text = ""
    if HAS_PYPDF2:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            for page in reader.pages[:10]:  # max 10 pages
                pdf_text += page.extract_text() or ""
        except Exception:
            pass

    if not pdf_text.strip():
        # Si pas de texte extractible, envoyer comme image (première page)
        # On utilise le PDF directement via l'API document
        client = anthropic.Anthropic(api_key=api_key)
        b64_data = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "document",
                                "source": {
                                    "type": "base64",
                                    "media_type": "application/pdf",
                                    "data": b64_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": EXTRACTION_PROMPT,
                            },
                        ],
                    }
                ],
            )
            return _parse_extraction_response(response.content[0].text)
        except Exception:
            return {}

    # Envoyer le texte extrait au LLM
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": f"Voici le texte extrait d'un document (devis/fiche technique) :\n\n{pdf_text[:8000]}\n\n{EXTRACTION_PROMPT}",
                }
            ],
        )
        return _parse_extraction_response(response.content[0].text)
    except Exception:
        return {}


def extract_from_file(file_bytes: bytes, filename: str) -> dict:
    """Point d'entrée : extrait les informations selon le type de fichier."""
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        return extract_from_pdf(file_bytes)

    # Images
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }

    for ext, mime in mime_map.items():
        if filename_lower.endswith(ext):
            return extract_from_image(file_bytes, mime)

    return {}
