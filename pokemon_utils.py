import re


PREFIXES = (
    "BG ",
    "Shadow ",
    "Mega ",
    "Primal ",
    "Origin Forme ",
    "Altered Forme ",
    "Dawn Wings ",
    "Dusk Mane ",
    "✨ Shiny ",
)


def normalize_pokemon(name: str) -> str:
    """
    Normalise le nom d'un Pokémon.

    Exemples :
        Shadow Palkia -> Palkia
        BG Shadow Mewtwo -> Mewtwo
        Origin Forme Dialga -> Dialga
    """

    if not name:
        return ""

    name = name.strip()

    changed = True

    while changed:
        changed = False

        for prefix in PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True

    if name.endswith(" caught!"):
        name = name[:-8]

    return " ".join(name.split()).title()


def emoji_key(name: str) -> str:
    """
    Transforme un nom Pokémon en clé du dictionnaire POKEMON_EMOJIS.

    Exemples :
        Ho-Oh -> ho_oh
        Tapu Koko -> tapu_koko
    """

    return (
        normalize_pokemon(name)
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


def sql_normalize_pokemon() -> str:
    """
    Expression SQL utilisée dans les WHERE.

    Permet de considérer :
        Shadow Palkia
        BG Shadow Palkia
        Origin Forme Palkia
        etc.
    comme étant simplement Palkia.
    """

    expr = "pokemon"

    replacements = [
        "BG ",
        "Shadow ",
        "Mega ",
        "Primal ",
        "Origin Forme ",
        "Altered Forme ",
        "Dawn Wings ",
        "Dusk Mane ",
        "✨ Shiny ",
    ]

    for r in replacements:
        expr = f"REPLACE({expr}, '{r}', '')"

    return expr
