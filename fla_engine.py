"""
Moteur de règles FLA - Encode la procédure "Procédure pour compléter FLA IA"
Logique déterministe pour décider des valeurs de chaque champ.
"""

from datetime import date

# --- Constantes ---
SERVICE_DEMANDEUR = "Laboratoire de biologie clinique"
SITE_DEFAULT = "CHR Citadelle – laboratoire de biologie clinique"
LOCAL_DEFAULT = "Local existant (laboratoire) – pas de local supplémentaire"
DATE_DEFAULT = "Dès validation"
QUANTITE_DEFAULT = 1
MONTANT_DEFAULT = "Selon devis joint"

# Catégories d'achat (depuis onglet Données)
CATEGORIES_ACHAT = [
    "ALIMENTATION/HORECA",
    "ELECTRO/AUDIOVISUEL/TELEPHONIE",
    "FLEET",
    "FOURNITURES BUREAU",
    "GESTION DES DECHETS",
    "HYGIENE/PROTECTION INDIVIDUELLE (EPI)",
    "INFORMATIQUE HORS MEDICAL",
    "INFORMATIQUE MEDICAL",
    "LABORATOIRE",
    "MEDICAL",
    "MOBILIER",
    "NETTOYAGE/LINGERIE/TENUES",
    "PHARMACIE",
    "SERVICES GENERAUX",
    "TECHNIQUE ET INFRASTRUCTURE",
]

# Raisons d'achat (depuis onglet Données)
RAISONS_ACHAT = [
    "Remplacement /éch standard matériel vétuste ou défectueux",
    "Remplacement /éch standard matériel cassé par une mauvaise manipulation",
    "Remplacement matériel perdu",
    "Extension du parc existant / \naugmentation de l'activité existante",
    "Amélioration de l'existant (qualité, \nsécurité, innovation, etc.)",
    "Nouvelle activité",
    "Autre : spécifier dans la case suivante",
]

# Options reprise matériel
OPTIONS_REPRISE = ["Oui", "Non", "Ne sais pas"]

# Options budget
OPTIONS_BUDGET = ["Oui ", "Non ", "En cours de demande à la cellule budget"]

# Options consommables/maintenance (depuis onglet Données)
OPTIONS_CONSOMMABLES = [
    "Pas de consommables",
    "Consommables non-médicaux",
    "Consommables médicaux stériles",
    "Consommables médicaux non-stériles",
    "Consommables médicaux stériles ET non-stériles",
    "Ne sais pas",
]

OPTIONS_MAINTENANCE = [
    "Omnium",
    "Semi-omnium",
    "Préventive",
    "Interne à l'institution",
    "Pas de maintenance",
    "Ne sais pas",
]

# Options IT
OPTIONS_IT = [
    "Aucune intervention de l'IT",
    "Equipement IT nécessaire (PC, serveur, etc)",
    "Connexion nécessaire (Wifi, câble)",
    "Intégration au système IT nécessaire (DPI, etc)",
    "Plusieurs interventions de l'IT (équipement, connexions,  intégrations)",
    "Ne sais pas",
]

# Mots-clés pour la détection automatique
KEYWORDS_IT = [
    "logiciel", "software", "serveur", "pc", "ordinateur", "informatique",
    "dpi", "intégration", "interface", "middleware", "lis", "lims",
    "réseau", "wifi", "connexion", "imprimante réseau",
]

KEYWORDS_RGPD = [
    "logiciel", "software", "cloud", "saas", "données patient",
    "dpi", "interface", "middleware", "lis", "lims", "télémédecine",
    "serveur", "accès distant", "remote", "maintenance à distance",
]

KEYWORDS_EQUIPEMENT_LABO = [
    "analyseur", "automate", "centrifugeuse", "microscope", "spectromètre",
    "photomètre", "incubateur", "étuve", "réfrigérateur", "congélateur",
    "hotte", "agitateur", "balance", "pipette électronique", "bain-marie",
    "cytomètre", "séquenceur", "pcr", "thermocycleur", "lecteur",
    "colorateur", "enrobeuse", "microtome", "cryostat",
]

KEYWORDS_CONSOMMABLES = [
    "tube", "aiguille", "réactif", "kit", "plaque", "lame", "lamelle",
    "embout", "pipette", "seringue", "cuvette", "bandelette", "cartouche",
    "filtre", "membrane", "colonne", "tampon", "solution",
]

KEYWORDS_MOBILIER = [
    "armoire", "étagère", "bureau", "chaise", "tabouret", "chariot",
    "table", "meuble", "rangement", "casier", "poubelle", "bac",
]


def determine_raison_achat(objet: str, contexte: str, is_remplacement: bool, raison_user: str = "") -> str:
    """Détermine la raison de l'achat selon la procédure."""
    if raison_user:
        return raison_user

    text = (objet + " " + contexte).lower()

    if is_remplacement:
        if "cassé" in text or "manipulation" in text or "casse" in text:
            return RAISONS_ACHAT[1]  # cassé par mauvaise manipulation
        elif "perdu" in text or "perte" in text:
            return RAISONS_ACHAT[2]  # perdu
        else:
            return RAISONS_ACHAT[0]  # vétuste ou défectueux

    if any(w in text for w in ["nouveau test", "nouvelle offre", "nouvelle prestation", "nouvelle activité", "nouveau paramètre"]):
        return RAISONS_ACHAT[5]  # Nouvelle activité

    if any(w in text for w in ["augmentation", "supplémentaire", "volume", "extension", "renfort"]):
        return RAISONS_ACHAT[3]  # Extension

    if any(w in text for w in ["amélioration", "qualité", "sécurité", "innovation", "optimisation", "mise à jour", "upgrade"]):
        return RAISONS_ACHAT[4]  # Amélioration

    return RAISONS_ACHAT[5]  # Nouvelle activité par défaut pour le labo


def determine_categorie(objet: str, categorie_user: str = "") -> str:
    """Détermine la catégorie d'achat."""
    if categorie_user:
        return categorie_user

    text = objet.lower()

    if any(w in text for w in KEYWORDS_IT + ["logiciel", "software", "licence"]):
        if any(w in text for w in ["médical", "labo", "lis", "lims", "dpi"]):
            return "INFORMATIQUE MEDICAL"
        return "INFORMATIQUE HORS MEDICAL"

    if any(w in text for w in KEYWORDS_EQUIPEMENT_LABO + KEYWORDS_CONSOMMABLES + ["réactif", "analyseur", "automate"]):
        return "LABORATOIRE"

    if any(w in text for w in ["médical", "chirurgical", "patient", "clinique"]):
        return "MEDICAL"

    if any(w in text for w in KEYWORDS_MOBILIER):
        return "MOBILIER"

    return "LABORATOIRE"  # défaut pour le labo


def determine_site(user_site: str = "") -> str:
    """Détermine le site concerné."""
    if user_site and user_site.strip():
        return user_site.strip()
    return SITE_DEFAULT


def determine_local(user_local: str = "") -> str:
    """Détermine le local."""
    if user_local and user_local.strip():
        return user_local.strip()
    return LOCAL_DEFAULT


def determine_consommables(objet: str, user_choice: str = "") -> str:
    """Détermine s'il y a des consommables dédiés."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in KEYWORDS_MOBILIER):
        return "Pas de consommables"

    if any(w in text for w in KEYWORDS_EQUIPEMENT_LABO):
        return "Ne sais pas"

    if any(w in text for w in KEYWORDS_CONSOMMABLES):
        return "Pas de consommables"  # l'objet EST un consommable

    return "Ne sais pas"


def determine_maintenance(objet: str, has_devis_maintenance: bool = False, user_choice: str = "") -> str:
    """Détermine la maintenance nécessaire."""
    if user_choice:
        return user_choice

    if has_devis_maintenance:
        return "Ne sais pas"  # le devis en parle, à confirmer

    text = objet.lower()

    if any(w in text for w in KEYWORDS_MOBILIER + KEYWORDS_CONSOMMABLES):
        return "Pas de maintenance"

    if any(w in text for w in KEYWORDS_EQUIPEMENT_LABO):
        return "Ne sais pas"

    return "Ne sais pas"


def determine_it(objet: str, user_choice: str = "") -> str:
    """Détermine les besoins IT."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in ["logiciel", "software", "licence", "saas", "cloud"]):
        return "Intégration au système IT nécessaire (DPI, etc)"

    if any(w in text for w in ["interface", "middleware", "intégration", "dpi", "lis", "lims"]):
        return "Intégration au système IT nécessaire (DPI, etc)"

    if any(w in text for w in ["serveur", "pc", "ordinateur"]):
        return "Equipement IT nécessaire (PC, serveur, etc)"

    if any(w in text for w in ["wifi", "réseau", "connexion"]):
        return "Connexion nécessaire (Wifi, câble)"

    # Certains équipements de labo nécessitent souvent une connexion
    if any(w in text for w in ["analyseur", "automate"]):
        return "Connexion nécessaire (Wifi, câble)"

    return "Aucune intervention de l'IT"


def determine_rgpd(objet: str, user_choice: str = "") -> str:
    """Détermine si le fournisseur a accès aux données patients."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in KEYWORDS_RGPD):
        return "Oui"

    # Analyseurs avec connexion réseau → maintenance à distance possible
    if any(w in text for w in ["analyseur", "automate"]) and any(w in text for w in ["connecté", "réseau", "interface"]):
        return "Oui"

    return "Non"


def determine_travaux(objet: str, user_choice: str = "") -> str:
    """Détermine si des travaux sont nécessaires."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in ["installation", "raccordement", "plomberie", "électricité", "ventilation"]):
        return "Oui"

    # Gros équipements de labo peuvent nécessiter des travaux
    if any(w in text for w in ["automate", "chaîne"]) and any(w in text for w in ["installation", "nouveau"]):
        return "Oui"

    return "Non"


def determine_sipp(objet: str, user_choice: str = "") -> str:
    """Détermine si le SIPP doit intervenir."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in ["chimique", "dangereux", "toxique", "radioactif", "laser", "rayon"]):
        return "Oui"

    return "Non"


def determine_hygiene(objet: str, user_choice: str = "") -> str:
    """Détermine si les hygiénistes doivent intervenir."""
    if user_choice:
        return user_choice

    text = objet.lower()

    if any(w in text for w in ["stérile", "désinfection", "décontamination", "salle blanche"]):
        return "Oui"

    return "Non"


def determine_formation(objet: str) -> str:
    """Détermine si une formation est nécessaire."""
    text = objet.lower()
    if any(w in text for w in KEYWORDS_EQUIPEMENT_LABO + ["logiciel", "software"]):
        return "Oui"
    return "Non"


def determine_tests(objet: str) -> str:
    """Détermine si des tests sont nécessaires."""
    text = objet.lower()
    if any(w in text for w in KEYWORDS_EQUIPEMENT_LABO + ["logiciel", "software", "réactif", "kit"]):
        return "Oui"
    return "Non"


def determine_remplacement_info(is_remplacement: bool, marque_ancien: str = "") -> str:
    """Info sur le matériel à remplacer."""
    if not is_remplacement:
        return "Sans objet"
    if marque_ancien and marque_ancien.strip():
        return marque_ancien.strip()
    return "À confirmer"


def determine_reprise(is_remplacement: bool, user_choice: str = "") -> str:
    """Reprise de l'ancien matériel par la firme."""
    if user_choice:
        return user_choice
    if not is_remplacement:
        return "Non"
    return "Ne sais pas"


def build_fla_data(form_inputs: dict) -> dict:
    """
    Construit le dictionnaire complet {champ: valeur} pour remplir la FLA.

    form_inputs attendu :
        objet: str (obligatoire)
        contexte: str
        categorie: str (optionnel, sera déduit sinon)
        quantite: int
        prix_unitaire: str
        montant_total: str
        date_souhaitee: str
        site: str
        local: str
        is_remplacement: bool
        remplacement_info: str (marque/modèle ancien)
        fournisseurs: str
        devis_disponible: bool
        compatibilite: str
        budget_prevu: str
        consommables: str (choix user)
        estimation_consommables: str
        maintenance: str (choix user)
        estimation_maintenance: str
        commentaires_budget: str
        subside: str
        nb_patients: str
        code_inami: str
        montant_inami: str
        pct_hopital_inami: str
        ressources_humaines: str
        categories_rh: str
        travaux: str (choix user)
        estimation_travaux: str
        it: str (choix user)
        estimation_it: str
        rgpd: str (choix user)
        sipp: str (choix user)
        hygiene: str (choix user)
        autres_parties: str
        nom_demandeur: str
        motivation: str (généré par LLM ou template)
        rentabilite: str (généré par LLM ou template)
    """
    objet = form_inputs.get("objet", "")
    contexte = form_inputs.get("contexte", "")
    is_remplacement = form_inputs.get("is_remplacement", False)

    data = {}

    # Date
    data["date"] = form_inputs.get("date_souhaitee", "") or date.today().strftime("%d/%m/%Y")

    # Service demandeur
    data["service_demandeur"] = SERVICE_DEMANDEUR

    # Nom demandeur
    data["nom_demandeur"] = form_inputs.get("nom_demandeur", "")

    # Catégorie
    data["categorie"] = determine_categorie(objet, form_inputs.get("categorie", ""))

    # Objet
    data["objet"] = objet

    # Raison
    data["raison"] = determine_raison_achat(
        objet, contexte, is_remplacement, form_inputs.get("raison", "")
    )

    # Motivation (vient du LLM ou template - passé en input)
    data["motivation"] = form_inputs.get("motivation", "")

    # Remplacement
    data["remplacement_info"] = determine_remplacement_info(
        is_remplacement, form_inputs.get("remplacement_info", "")
    )

    # Reprise
    data["reprise"] = determine_reprise(is_remplacement, form_inputs.get("reprise", ""))

    # Compatibilité
    data["compatibilite"] = form_inputs.get("compatibilite", "") or "Sans objet"

    # Site
    data["site"] = determine_site(form_inputs.get("site", ""))

    # Local
    data["local"] = determine_local(form_inputs.get("local", ""))

    # Fournisseurs
    data["fournisseurs"] = form_inputs.get("fournisseurs", "")

    # Devis
    data["devis_disponible"] = "Oui (transmis avec la fiche)" if form_inputs.get("devis_disponible", False) else "Non"

    # Date mise en service
    date_souhaitee = form_inputs.get("date_souhaitee", "")
    data["date_mise_en_service"] = date_souhaitee if date_souhaitee else DATE_DEFAULT

    # Quantité
    data["quantite"] = form_inputs.get("quantite", QUANTITE_DEFAULT) or QUANTITE_DEFAULT

    # Prix
    prix_unitaire = form_inputs.get("prix_unitaire", "")
    data["prix_unitaire"] = prix_unitaire if prix_unitaire else ""

    montant_total = form_inputs.get("montant_total", "")
    data["montant_total"] = montant_total if montant_total else MONTANT_DEFAULT

    # Budget
    data["budget_prevu"] = form_inputs.get("budget_prevu", "") or ""

    # Consommables
    data["consommables"] = determine_consommables(objet, form_inputs.get("consommables", ""))
    estimation_conso = form_inputs.get("estimation_consommables", "")
    if data["consommables"] == "Pas de consommables":
        data["estimation_consommables"] = "Sans objet"
    elif estimation_conso:
        data["estimation_consommables"] = estimation_conso
    else:
        data["estimation_consommables"] = "À confirmer"

    # Maintenance
    data["maintenance"] = determine_maintenance(
        objet,
        form_inputs.get("has_devis_maintenance", False),
        form_inputs.get("maintenance", ""),
    )
    estimation_maint = form_inputs.get("estimation_maintenance", "")
    if data["maintenance"] == "Pas de maintenance":
        data["estimation_maintenance"] = "Sans objet"
    elif estimation_maint:
        data["estimation_maintenance"] = estimation_maint
    else:
        data["estimation_maintenance"] = "À confirmer"

    # Commentaires budget
    data["commentaires_budget"] = form_inputs.get("commentaires_budget", "")

    # Rentabilité (vient du LLM ou template)
    data["rentabilite"] = form_inputs.get("rentabilite", "")

    # Subside
    data["subside"] = form_inputs.get("subside", "") or "Non"

    # INAMI / RH (pour matériel médical > 30k)
    data["nb_patients"] = form_inputs.get("nb_patients", "") or "Sans objet"
    data["code_inami"] = form_inputs.get("code_inami", "") or "Sans objet"
    data["montant_inami"] = form_inputs.get("montant_inami", "") or "Sans objet"
    data["pct_hopital_inami"] = form_inputs.get("pct_hopital_inami", "") or "Sans objet"
    data["ressources_humaines"] = form_inputs.get("ressources_humaines", "") or "Sans objet"
    data["categories_rh"] = form_inputs.get("categories_rh", "") or "Sans objet"

    # Travaux
    data["travaux"] = determine_travaux(objet, form_inputs.get("travaux", ""))
    data["estimation_travaux"] = form_inputs.get("estimation_travaux", "") or ""

    # IT
    data["it"] = determine_it(objet, form_inputs.get("it", ""))
    data["estimation_it"] = form_inputs.get("estimation_it", "") or ""

    # RGPD
    data["rgpd"] = determine_rgpd(objet, form_inputs.get("rgpd", ""))

    # SIPP
    data["sipp"] = determine_sipp(objet, form_inputs.get("sipp", ""))

    # Hygiène
    data["hygiene"] = determine_hygiene(objet, form_inputs.get("hygiene", ""))

    # Autres parties prenantes
    data["autres_parties"] = form_inputs.get("autres_parties", "")

    # Formation / Tests
    data["formation"] = determine_formation(objet)
    data["tests"] = determine_tests(objet)

    return data


def generate_summary(data: dict) -> str:
    """Génère le résumé court de la FLA."""
    points_a_confirmer = []
    for key, val in data.items():
        if isinstance(val, str) and "à confirmer" in val.lower():
            points_a_confirmer.append(key.replace("_", " ").title())

    it_rgpd = []
    if data.get("it", "") != "Aucune intervention de l'IT":
        it_rgpd.append(f"IT : {data.get('it', 'N/A')}")
    if data.get("rgpd", "") == "Oui":
        it_rgpd.append("RGPD : Oui")

    summary = f"""**Objet** : {data.get('objet', 'N/A')}
**Raison** : {data.get('raison', 'N/A')}
**Budget** : {data.get('montant_total', 'N/A')} (Qté: {data.get('quantite', 1)})
**IT / RGPD** : {', '.join(it_rgpd) if it_rgpd else 'Aucune implication'}
**Points à confirmer** : {', '.join(points_a_confirmer) if points_a_confirmer else 'Aucun'}"""

    return summary
