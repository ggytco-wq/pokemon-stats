import discord


class DexSelect(discord.ui.Select):

    def __init__(self):

        options = [
            discord.SelectOption(
                label="Chargement...",
                value="loading"
            )
        ]

        super().__init__(
            placeholder="Choisir un Pokémon",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
