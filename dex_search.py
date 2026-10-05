def normalize_name(name: str) -> str:
    return (
        name.lower()
        .replace("♀", "")
        .replace("♂", "")
        .replace("-", "")
        .replace(" ", "")
    )


def search_pokemon(data, query):

    query = normalize_name(query)

    results = []

    for pokemon in data:

        if query in normalize_name(pokemon["name"]):
            results.append(pokemon)

    return results
