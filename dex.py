import discord
from discord.ext import commands
from discord import app_commands


class Dex(commands.Cog):

    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(
        name="iiode_dex_v3",
        description="Nouvelle version du Pokédex IIODE"
    )
    async def iiode_dex_v3(
        self,
        interaction: discord.Interaction
    ):

        embed = discord.Embed(
            title="📖 Pokédex IIODE V3",
            description="Le nouveau Pokédex est en cours de construction.",
            color=discord.Color.gold()
        )

        embed.add_field(
            name="État",
            value="✅ Module chargé",
            inline=False
        )

        await interaction.response.send_message(
            embed=embed
        )


async def setup(bot):
    await bot.add_cog(Dex(bot))
