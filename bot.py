import discord
from discord.ext import commands, tasks
import datetime
import aiosqlite
import os
import re
import asyncio
import aiohttp
from emojis import POKEMON_EMOJIS

from pokemon_utils import (
    normalize_pokemon,
    emoji_key,
    sql_normalize_pokemon,
)
print("TEST IMPORT EMOJI :", POKEMON_EMOJIS.get("mewtwo"))
DEBUG = False
if DEBUG:
    print("message")

LEGENDARIES = [
    "Articuno", "Zapdos", "Moltres",
    "mewtwo", "Mew",
    "Raikou", "Entei", "Suicune",
    "Lugia", "Ho-Oh", "Celebi",
    "Regirock", "Regice", "Registeel",
    "Latias", "Latios",
    "kyogre", "Groudon", "Rayquaza",
    "Jirachi", "Deoxys",
    "Uxie", "Mesprit", "Azelf",
    "Dialga", "Palkia", "Heatran",
    "Regigigas", "Giratina", "Cresselia",
    "Phione", "Manaphy", "Darkrai",
    "Shaymin", "Arceus",
    "Victini",
    "Cobalion", "Terrakion", "Virizion",
    "Tornadus", "Thundurus", "Landorus",
    "Reshiram", "Zekrom", "Kyurem",
    "Keldeo", "Meloetta", "Genesect",
    "Xerneas", "Yveltal", "Zygarde",
    "Diancie", "Hoopa", "Volcanion",
    "Type: Null", "Silvally",
    "Tapu Koko", "Tapu Lele",
    "Tapu Bulu", "Tapu Fini",
    "Cosmog", "Cosmoem",
    "Solgaleo", "Lunala", "Necrozma",
    "Magearna", "Marshadow",
    "Zeraora", "Meltan", "Melmetal",
    "Zacian", "Zamazenta", "Eternatus",
    "Kubfu", "Urshifu",
    "Regieleki", "Regidrago",
    "Glastrier", "Spectrier",
    "Calyrex",
    "Enamorus",
    "Koraidon", "Miraidon"
]

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID")
GUILD_ID_RAW = os.getenv("GUILD_ID")

print("===== RAILWAY ENV =====")
print("CHANNEL_ID =", repr(CHANNEL_ID_RAW))
print("GUILD_ID   =", repr(GUILD_ID_RAW))
print("TOKEN      =", "OK" if TOKEN else "ABSENT")
print("=======================")

if not CHANNEL_ID_RAW:
    raise RuntimeError("CHANNEL_ID manquant dans Railway")

if not GUILD_ID_RAW:
    raise RuntimeError("GUILD_ID manquant dans Railway")

CHANNEL_ID = int(CHANNEL_ID_RAW)
GUILD_ID = int(GUILD_ID_RAW)

ACTIVE_CATEGORY = "🔥 Clients actifs"
INACTIVE_CATEGORY = "📦 Clients inactifs"

# Change le nom pour repartir sur une base propre
VOLUME_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH")

if VOLUME_PATH:
    DB_NAME = os.path.join(VOLUME_PATH, "pokemon3.db")
else:
    DB_NAME = "pokemon3.db"

print("DATABASE :", DB_NAME)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents
)
HISTORY_READY = asyncio.Event()
HISTORY_IMPORT_LOCK = asyncio.Lock()
async def load_application_emojis():

    print("===== CHARGEMENT APPLICATION EMOJIS =====")

    try:
        application_id = bot.application_id

        if not application_id:
            app_info = await bot.application_info()
            application_id = app_info.id

        url = (
            f"https://discord.com/api/v10/"
            f"applications/{application_id}/emojis"
        )

        headers = {
            "Authorization": f"Bot {TOKEN}"
        }

        timeout = aiohttp.ClientTimeout(
            total=30
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.get(
                url,
                headers=headers
            ) as response:

                if response.status != 200:

                    text = await response.text()

                    print(
                        "Erreur Application Emojis :",
                        response.status,
                        text[:500]
                    )

                    return 0

                data = await response.json(
                    content_type=None
                )

        emojis = data.get("items", [])

        loaded = 0

        for emoji in emojis:

            name = emoji.get("name")
            emoji_id = emoji.get("id")

            if not name or not emoji_id:
                continue

            animated = emoji.get(
                "animated",
                False
            )

            if animated:
                emoji_text = (
                    f"<a:{name}:{emoji_id}>"
                )
            else:
                emoji_text = (
                    f"<:{name}:{emoji_id}>"
                )

            # Nom direct de l'application emoji
            key = name.lower()

            POKEMON_EMOJIS[key] = emoji_text

            loaded += 1

        # -----------------------------------------
        # ALIAS utiles pour pokemon_utils.emoji_key
        # -----------------------------------------

        aliases = {
            "type:_null": "type_null",
        }

        for wanted_key, discord_key in aliases.items():

            if discord_key in POKEMON_EMOJIS:

                POKEMON_EMOJIS[wanted_key] = (
                    POKEMON_EMOJIS[discord_key]
                )

        print(
            f"Application Emojis chargés : "
            f"{loaded}"
        )

        print(
            f"POKEMON_EMOJIS total : "
            f"{len(POKEMON_EMOJIS)}"
        )

        print(
            "Thundurus :",
            POKEMON_EMOJIS.get(
                "thundurus"
            )
        )

        print(
            "========================================"
        )

        return loaded

    except Exception as e:

        print(
            f"Erreur chargement emojis : {e}"
        )

        return 0

async def load_extensions():

    for filename in os.listdir("commands"):

        if filename.endswith(".py") and filename != "__init__.py":

            await bot.load_extension(
                f"commands.{filename[:-3]}"
            )

            print(f"Module chargé : {filename}")
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS catches(
            message_id TEXT PRIMARY KEY,
            username TEXT,
            pokemon TEXT,
            shiny INTEGER,
            background INTEGER,
            caught_at TEXT
        )
        """)
        await db.commit()


def extract_username(footer):
    """
    Exemples :

    50 x 50y EEEBBB333 · -23.58, -46.66
    100 Inerte12 · 37.51, 126.99
    200 y Cocotiernicolas@gmail.com · ...
    """

    if "·" not in footer:
        return None

    left = footer.split("·")[0].strip()

    username = re.sub(
        r'^(?:\d+\s*(?:x|y)?\s*)+',
        '',
        left
    ).strip()

    return username
async def get_or_create_category(guild, name):

    category = discord.utils.get(
        guild.categories,
        name=name
    )

    if category:
        return category

    try:
        category = await guild.create_category(name)
        print(f"Catégorie créée : {name}")
        return category

    except Exception as e:
        print(
            f"Erreur création catégorie {name} : {e}"
        )
        return None
def parse_catch_message(message):

    if not message.embeds:
        return None

    embed = message.embeds[0]

    title = embed.title or ""
    description = embed.description or ""

    if "caught!" not in title:
        return None

    pokemon = normalize_pokemon(title)

    shiny = 1 if "Shiny" in title else 0

    background = (
        1
        if "Background:" in description
        or title.startswith("BG ")
        else 0
    )

    footer = embed.footer.text if embed.footer else ""

    username = extract_username(footer)

    if not username:
        return None

    return (
        str(message.id),
        username,
        pokemon,
        shiny,
        background,
        message.created_at.isoformat()
    )


async def save_message(message):

    data = parse_catch_message(message)

    if data is None:
        return

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
            INSERT OR IGNORE INTO catches
            (
                message_id,
                username,
                pokemon,
                shiny,
                background,
                caught_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, data)

        await db.commit()
async def import_history(channel):

    async with HISTORY_IMPORT_LOCK:

        if HISTORY_READY.is_set():
            return

        print("===== IMPORT HISTORIQUE =====")

        async with aiosqlite.connect(DB_NAME) as db:

            batch = []

            scanned = 0
            saved = 0

            async for message in channel.history(
                limit=None,
                oldest_first=True
            ):

                scanned += 1

                data = parse_catch_message(message)

                if data is None:
                    continue

                batch.append(data)

                if len(batch) >= 500:

                    await db.executemany("""
                        INSERT OR IGNORE INTO catches
                        (
                            message_id,
                            username,
                            pokemon,
                            shiny,
                            background,
                            caught_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, batch)

                    await db.commit()

                    saved += len(batch)

                    print(
                        f"Import : {saved} captures enregistrées"
                    )

                    batch.clear()

            if batch:

                await db.executemany("""
                    INSERT OR IGNORE INTO catches
                    (
                        message_id,
                        username,
                        pokemon,
                        shiny,
                        background,
                        caught_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, batch)

                await db.commit()

                saved += len(batch)

        HISTORY_READY.set()

        print("===== IMPORT TERMINÉ =====")
        print(f"Messages analysés : {scanned}")
        print(f"Captures trouvées : {saved}")
@bot.event
async def on_ready():

    print(f"Connecté : {bot.user}")
    await load_application_emojis()

    await init_db()

    try:
        channel = await bot.fetch_channel(CHANNEL_ID)
        print(f"Salon trouvé : {channel.name}")

    except Exception as e:
        print(f"Impossible de récupérer le salon : {e}")
        return

    await import_history(channel)

    await refresh_client_channels()

    if not update_client_channels.is_running():
        update_client_channels.start()

    try:
        await load_extensions()

        synced = await bot.tree.sync()

        print(
            f"{len(synced)} commandes synchronisées."
        )

    except Exception as e:
        print(f"Erreur sync : {e}")

@bot.event
async def on_message(message):

    if message.channel.id != CHANNEL_ID:
        return

    await save_message(message)
    await refresh_client_channels()

@bot.tree.command(
    name="stats",
    description="Statistiques d'un joueur"
)
async def stats(
    interaction: discord.Interaction,
    joueur: str
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                COUNT(*),
                SUM(shiny),
                SUM(background)
            FROM catches
            WHERE username=?
        """, (joueur,))

        row = await cursor.fetchone()

    total = row[0] or 0
    shiny = row[1] or 0
    background = row[2] or 0

    embed = discord.Embed(
        title=f"📊 {joueur}"
    )

    embed.add_field(
        name="📦 Captures",
        value=str(total),
        inline=False
    )

    embed.add_field(
        name="✨ Shinies",
        value=str(shiny),
        inline=False
    )

    embed.add_field(
        name="🌄 Backgrounds",
        value=str(background),
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="classement",
    description="Classement des captures"
)
async def classement(
    interaction: discord.Interaction
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                username,
                COUNT(*) c
            FROM catches
            GROUP BY username
            ORDER BY c DESC
            LIMIT 10
        """)

        rows = await cursor.fetchall()

    texte = ""

    for i, row in enumerate(rows, 1):
        texte += (
            f"{i}. {row[0]} - "
            f"{row[1]} captures\n"
        )

    if texte == "":
        texte = "Aucune donnée."

    embed = discord.Embed(
        title="🏆 Classement",
        description=texte
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="shinies",
    description="Classement des shinies"
)
async def shinies(
    interaction: discord.Interaction
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                username,
                SUM(shiny) s
            FROM catches
            GROUP BY username
            ORDER BY s DESC
            LIMIT 10
        """)

        rows = await cursor.fetchall()

    texte = ""

    for i, row in enumerate(rows, 1):
        total = row[1] or 0
        texte += (
            f"{i}. {row[0]} - "
            f"✨ {total}\n"
        )

    if texte == "":
        texte = "Aucune donnée."

    embed = discord.Embed(
        title="✨ Classement des shinies",
        description=texte
    )

    await interaction.response.send_message(
        embed=embed
    )

@bot.tree.command(
    name="profil",
    description="Statistiques du jour d'un joueur"
)
async def profil(
    interaction: discord.Interaction,
    joueur: str
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                COUNT(*),
                SUM(shiny),
                SUM(background)
            FROM catches
            WHERE username=?
            AND DATE(caught_at)=DATE('now')
        """, (joueur,))

        row = await cursor.fetchone()

        cursor = await db.execute("""
            SELECT
                pokemon,
                COUNT(*) c
            FROM catches
            WHERE username=?
            AND DATE(caught_at)=DATE('now')
            GROUP BY pokemon
            ORDER BY c DESC
            LIMIT 1
        """, (joueur,))

        fav = await cursor.fetchone()

    total = row[0] or 0
    shiny = row[1] or 0
    bg = row[2] or 0

    pokemon_fav = "Aucun"
    nb_fav = 0

    if fav:
        pokemon_fav = fav[0]
        nb_fav = fav[1]

    embed = discord.Embed(
        title=f"📊 Profil du jour de {joueur}"
    )

    embed.add_field(
        name="📦 Captures",
        value=str(total),
        inline=True
    )

    embed.add_field(
        name="✨ Shinies",
        value=str(shiny),
        inline=True
    )

    embed.add_field(
        name="🌄 Backgrounds",
        value=str(bg),
        inline=True
    )

    embed.add_field(
        name="🥇 Pokémon le plus capturé",
        value=f"{pokemon_fav} ({nb_fav})",
        inline=False
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="iiode",
    description="Liste des comptes contenant iiode"
)
async def iiode(
    interaction: discord.Interaction
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                username,
                COUNT(*) c,
                SUM(shiny) s
            FROM catches
            WHERE LOWER(username) LIKE '%iiode%'
            GROUP BY username
            ORDER BY c DESC
        """)

        rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message(
            "Aucun compte iiode trouvé."
        )
        return

    texte = ""

    for username, total, shiny in rows:
        texte += (
            f"**{username}** - "
            f"{total} captures - "
            f"✨ {shiny or 0}\n"
        )

    embed = discord.Embed(
        title="📊 Comptes iiode",
        description=texte
    )

    await interaction.response.send_message(
        embed=embed
    )


@bot.tree.command(
    name="iiode_pokemon",
    description="Voir quel compte iiode possède un Pokémon"
)
async def iiode_pokemon(
    interaction: discord.Interaction,
    pokemon: str
):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                username,
                COUNT(*) c
            FROM catches
            WHERE LOWER(username) LIKE '%iiode%'
            AND LOWER(pokemon)=LOWER(?)
            GROUP BY username
            ORDER BY c DESC
        """, (normalize_pokemon(pokemon),))

        rows = await cursor.fetchall()

    if not rows:
        await interaction.response.send_message(
            f"Aucun {pokemon} trouvé."
        )
        return

    texte = ""

    for username, total in rows:
        texte += f"{username} - {total}\n"

    embed = discord.Embed(
        title=f"📊 {pokemon}",
        description=texte
    )

    await interaction.response.send_message(
        embed=embed
    )
@bot.tree.command(
    name="reload_emojis",
    description="Recharge les Application Emojis Discord"
)
async def reload_emojis(
    interaction: discord.Interaction
):

    await interaction.response.defer(
        ephemeral=True
    )

    count = await load_application_emojis()

    await interaction.followup.send(
        f"✅ {count} Application Emojis chargés.\n"
        f"📦 {len(POKEMON_EMOJIS)} emojis disponibles.",
        ephemeral=True
    )

@bot.tree.command(
    name="compte",
    description="Voir les captures du jour d'un compte"
)
async def compte(
    interaction: discord.Interaction,
    joueur: str
):
    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute("""
            SELECT
                COUNT(*)
            FROM catches
            WHERE username=?
            AND DATE(caught_at)=DATE('now')
        """, (joueur,))

        total = (await cursor.fetchone())[0]

        cursor = await db.execute("""
            SELECT
                pokemon,
                COUNT(*) c
            FROM catches
            WHERE username=?
            AND DATE(caught_at)=DATE('now')
            GROUP BY pokemon
            ORDER BY c DESC
        """, (joueur,))

        rows = await cursor.fetchall()

    if total == 0:
        await interaction.response.send_message(
            f"Aucune capture aujourd'hui pour {joueur}."
        )
        return

    texte = ""

    for pokemon, count in rows:
        texte += f"{pokemon} : {count}\n"

    embed = discord.Embed(
        title=f"📦 Captures du jour - {joueur}",
        description=texte
    )

    embed.set_footer(
        text=f"Total : {total} captures"
    )

    await interaction.response.send_message(
        embed=embed
    )
@tasks.loop(minutes=5)
async def update_client_channels():
    await bot.wait_until_ready()
    await refresh_client_channels()
async def refresh_client_channels():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        return

    active_cat = await get_or_create_category(
        guild,
        ACTIVE_CATEGORY
    )

    inactive_cat = await get_or_create_category(
        guild,
        INACTIVE_CATEGORY
    )

    now = datetime.datetime.now(datetime.UTC)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT
                username,
                MAX(caught_at)
            FROM catches
            GROUP BY username
        """)
        players = await cursor.fetchall()

    print(f"Players trouvés : {len(players)}")

    for username, last_capture in players:

        if not last_capture:
            continue

        try:
            last = datetime.datetime.fromisoformat(
                last_capture
            )

            if last.tzinfo is None:
                last = last.replace(
                    tzinfo=datetime.UTC
                )

        except Exception as e:
            print(
                f"Erreur date {username}: "
                f"{last_capture} ({e})"
            )
            continue

        delta = now - last
        #
        # nombre de captures du jour
        #
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute("""
                SELECT COUNT(*)
                FROM catches
                WHERE username=?
                AND DATE(caught_at,'localtime')
                    = DATE('now','localtime')
            """, (username,))

            total_today = (
                await cursor.fetchone()
            )[0]

            cursor = await db.execute("""
                SELECT caught_at
                FROM catches
                WHERE username=?
                ORDER BY caught_at DESC
                LIMIT 5
            """, (username,))

            rows = await cursor.fetchall()

        
        # recherche d'un salon existant
        #
        found = None
        duplicates = []

        for c in guild.text_channels:
            name = c.name

            if name.startswith("🔥 "):
                name = name[2:]
            elif name.startswith("📦 "):
                name = name[2:]

            if "・" in name:
                name = name.split("・")[0]

            name = name.strip()

            if name == username:
                duplicates.append(c)

        if duplicates:
            found = duplicates[0]

            # supprimer les doublons
            for extra in duplicates[1:]:
                print(f"Suppression doublon : {extra.name}")
                await extra.delete() 
                await asyncio.sleep(1)
        #
        # ACTIF (<4h)
        #
        if delta.total_seconds() <= 4 * 3600:

            new_name = (
                f"🔥 {username}・{total_today}"
            )[:100]

            if found:

                if found.name != new_name:
                    await found.edit(
                        name=new_name
                    )

                if found.category != active_cat:
                    await found.edit(
                        category=active_cat
                    )

            else:

                if len(active_cat.text_channels) < 50:
                    await guild.create_text_channel(
                        new_name,
                        category=active_cat
                    )
                else:
                    print(
                        "Catégorie actifs pleine."
                    )

        #
        # INACTIF (<24h)
        #
        elif delta.total_seconds() <= 24 * 3600:

            new_name = (
                f"📦 {username}・{total_today}"
            )[:100]

            if found:

                if found.name != new_name:
                    await found.edit(
                        name=new_name
                    )

                if found.category != inactive_cat:
                    await found.edit(
                        category=inactive_cat
                    )

            else:

                if len(inactive_cat.text_channels) < 50:
                    await guild.create_text_channel(
                        new_name,
                        category=inactive_cat
                    )
                else:
                    print(
                        "Catégorie inactifs pleine."
                    )

        #
        # SUPPRESSION (>24h)
        #
        else:

            if found:
                await found.delete()
                
def get_legendary_base(raw_name):
    """
    Transforme toutes les formes en légendaire de base.

    Exemples :
    Palkia (Origin) -> Palkia
    Origin Forme Palkia -> Palkia
    Zacian (Hero) -> Zacian
    Zacian (Crowned Sword) -> Zacian
    Mega Rayquaza -> Rayquaza
    Shadow Moltres -> Moltres
    Primal Kyogre -> Kyogre
    Deoxys (Defense) -> Deoxys
    Giratina (Origin) -> Giratina
    Lunala -> Lunala
    """

    if not raw_name:
        return None

    name = str(raw_name).lower().strip()

    # Nettoyage général
    name = name.replace("caught!", " ")
    name = name.replace("✨", " ")

    # Tout caractère spécial devient un espace
    # Zacian(Hero) -> zacian hero
    # Palkia-Origin -> palkia origin
    name = re.sub(r"[^a-z0-9]+", " ", name)

    name = re.sub(r"\s+", " ", name).strip()

    # Cherche le nom de base comme un MOT COMPLET.
    # Important pour éviter que "Mew" corresponde à "Mewtwo".
    for legendary in sorted(
        LEGENDARIES,
        key=len,
        reverse=True
    ):

        base = legendary.lower()

        base = re.sub(
            r"[^a-z0-9]+",
            " ",
            base
        )

        base = re.sub(
            r"\s+",
            " ",
            base
        ).strip()

        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(base)
            + r"(?![a-z0-9])"
        )

        if re.search(pattern, name):
            return legendary

    return None


@bot.tree.command(
    name="iiode_dex",
    description="Liste tous les légendaires présents sur les comptes iiode"
)
async def iiode_dex(interaction: discord.Interaction):

    await interaction.response.defer()

    if not HISTORY_READY.is_set():

        await interaction.followup.send(
            "⏳ La base Pokémon est encore en cours de chargement."
        )

        return

    found_any = False

    # Nombre maximum de comptes affichés par page
    ACCOUNTS_PER_PAGE = 20

    async with aiosqlite.connect(DB_NAME) as db:

        for pokemon in LEGENDARIES:

            # -----------------------------------------
            # Recherche du Pokémon + toutes ses formes
            # -----------------------------------------

            if pokemon.lower() == "mew":

                cursor = await db.execute("""
                    SELECT
                        username,
                        COUNT(*) AS total,
                        COALESCE(SUM(shiny), 0) AS shinies,
                        COALESCE(SUM(background), 0) AS backgrounds

                    FROM catches

                    WHERE LOWER(username) LIKE '%iiode%'

                    AND LOWER(pokemon) LIKE '%mew%'

                    AND LOWER(pokemon) NOT LIKE '%mewtwo%'

                    GROUP BY username

                    ORDER BY total DESC
                """)

            else:

                search = f"%{pokemon.lower()}%"

                cursor = await db.execute("""
                    SELECT
                        username,
                        COUNT(*) AS total,
                        COALESCE(SUM(shiny), 0) AS shinies,
                        COALESCE(SUM(background), 0) AS backgrounds

                    FROM catches

                    WHERE LOWER(username) LIKE '%iiode%'

                    AND LOWER(pokemon) LIKE ?

                    GROUP BY username

                    ORDER BY total DESC
                """, (search,))

            rows = await cursor.fetchall()

            if not rows:
                continue

            found_any = True

            # -----------------------------------------
            # Nom propre affiché
            # -----------------------------------------

            if pokemon.lower() == "mewtwo":
                display_name = "Mewtwo"

            elif pokemon.lower() == "kyogre":
                display_name = "Kyogre"

            else:
                display_name = pokemon

            # -----------------------------------------
            # Totaux
            # -----------------------------------------

            total_catches = sum(
                row[1] or 0
                for row in rows
            )

            total_shiny = sum(
                row[2] or 0
                for row in rows
            )

            total_background = sum(
                row[3] or 0
                for row in rows
            )

            # -----------------------------------------
            # Emoji
            # -----------------------------------------

            emoji = POKEMON_EMOJIS.get(
                emoji_key(display_name),
                "🔹"
            )

            # -----------------------------------------
            # Découpage par comptes
            #
            # PLUS de découpage par caractères.
            # 20 comptes maximum par page.
            # -----------------------------------------

            pages = []

            for start in range(
                0,
                len(rows),
                ACCOUNTS_PER_PAGE
            ):

                page_rows = rows[
                    start:
                    start + ACCOUNTS_PER_PAGE
                ]

                pages.append(page_rows)

            total_pages = len(pages)

            # -----------------------------------------
            # Envoi de CHAQUE page
            # -----------------------------------------

            for page_number, page_rows in enumerate(
                pages,
                start=1
            ):

                lines = []

                for (
                    username,
                    total,
                    shinies,
                    backgrounds
                ) in page_rows:

                    lines.append(
                        f"• **{username}** : "
                        f"📦 {total} | "
                        f"✨ {shinies or 0} | "
                        f"🌄 {backgrounds or 0}"
                    )

                accounts_text = "\n".join(lines)

                # -----------------------------------------
                # Titre
                # -----------------------------------------

                if total_pages > 1:

                    title = (
                        f"{emoji} {display_name} "
                        f"— {page_number}/{total_pages}"
                    )

                else:

                    title = (
                        f"{emoji} {display_name}"
                    )

                # -----------------------------------------
                # Totaux visibles sur CHAQUE page
                # -----------------------------------------

                description = (
                    f"**Total :** "
                    f"📦 **{total_catches}** | "
                    f"✨ **{total_shiny}** | "
                    f"🌄 **{total_background}**\n"
                    f"👤 **{len(rows)} comptes**\n\n"
                    f"{accounts_text}"
                )

                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=discord.Color.gold()
                )

                # Informations sur la plage affichée
                first_position = (
                    (page_number - 1)
                    * ACCOUNTS_PER_PAGE
                    + 1
                )

                last_position = min(
                    page_number
                    * ACCOUNTS_PER_PAGE,
                    len(rows)
                )

                embed.set_footer(
                    text=(
                        f"Comptes "
                        f"{first_position}-{last_position}"
                        f" / {len(rows)}"
                    )
                )

                await interaction.followup.send(
                    embed=embed
                )

                # petite pause pour éviter de spammer
                # l'API Discord si beaucoup de pages
                await asyncio.sleep(0.3)

    if not found_any:

        await interaction.followup.send(
            "Aucun légendaire trouvé."
        )
bot.run(TOKEN)
