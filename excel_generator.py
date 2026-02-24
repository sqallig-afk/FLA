"""
Générateur Excel - Charge le template FLA et remplit les cellules de réponse.
"""

import io
import copy
from pathlib import Path

import openpyxl


TEMPLATE_PATH = Path(__file__).parent / "templates" / "fla_template.xlsx"

# Mapping : clé du dict fla_data → cellule Excel dans l'onglet "1 Lancement utilisateur"
CELL_MAPPING = {
    "date":                   "B7",
    "service_demandeur":      "B8",
    "nom_demandeur":          "B9",
    "categorie":              "B10",
    # B11 vide (pas de champ)
    # B12 = section header "Informations de Base et Motivation"
    "objet":                  "B13",
    "raison":                 "B14",
    "motivation":             "B15",
    "remplacement_info":      "B16",
    "reprise":                "B17",
    "compatibilite":          "B18",
    "site":                   "B19",
    "local":                  "B20",
    "fournisseurs":           "B21",
    "devis_disponible":       "B22",
    "date_mise_en_service":   "B23",
    # B24 vide
    # B25 = section header "Budget / Estimation"
    "quantite":               "B26",
    "prix_unitaire":          "B27",
    "montant_total":          "B28",
    "budget_prevu":           "B29",
    # B30 = section header "Si applicable => Consommables"
    "consommables":           "B31",
    "estimation_consommables":"B32",
    # B33 = section header "Si applicable => Maintenance"
    "maintenance":            "B34",
    "estimation_maintenance": "B35",
    "commentaires_budget":    "B36",
    # B37 vide
    # B38 = section header "Rentabilité"
    "rentabilite":            "B39",
    "subside":                "B40",
    # B41 = section header INAMI
    "nb_patients":            "B42",
    "code_inami":             "B43",
    "montant_inami":          "B44",
    "pct_hopital_inami":      "B45",
    "ressources_humaines":    "B46",
    "categories_rh":          "B47",
    # B48 vide
    # B49 = section header "Autres parties prenantes"
    "travaux":                "B50",
    "estimation_travaux":     "B51",
    "it":                     "B52",
    "estimation_it":          "B53",
    "rgpd":                   "B54",
    "sipp":                   "B55",
    "hygiene":                "B56",
    "autres_parties":         "B57",
    # B58 vide
    # B59 = section header "Autres informations"
    "formation":              "B60",
    "tests":                  "B61",
}


def generate_excel(fla_data: dict) -> bytes:
    """
    Charge le template Excel, remplit les cellules, retourne le fichier en bytes.

    Args:
        fla_data: dict retourné par fla_engine.build_fla_data()

    Returns:
        bytes du fichier .xlsx complété
    """
    wb = openpyxl.load_workbook(str(TEMPLATE_PATH))
    ws = wb["1 Lancement utilisateur "]

    for field_name, cell_ref in CELL_MAPPING.items():
        value = fla_data.get(field_name, "")
        if value is not None and value != "":
            ws[cell_ref] = value

    # Sauvegarder dans un buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
