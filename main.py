import discord
from discord import app_commands
from discord.ext import commands
import os
import random

from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot instance
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready and connected."""
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        # Syncing globally (might take up to an hour to appear, usually faster)
        # For instant sync during development, sync to a specific guild:
        # await bot.tree.sync(guild=discord.Object(id=YourGuildID))
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    print('------')

@bot.command()
async def sync(ctx):
    """Syncs slash commands to the current guild for instant updates."""
    # Copy global commands to this guild
    bot.tree.copy_global_to(guild=ctx.guild)
    # Sync just this guild
    await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"Synced commands to this server! You may need to restart your Discord client (Ctrl+R) if they don't appear immediately.")

# --- Slash Commands (start with /) ---

@bot.tree.command(name="ping", description="Replies with Pong! (Slash Version)")
async def slash_ping(interaction: discord.Interaction):
    """Slash command that replies with Pong!"""
    await interaction.response.send_message("Pong! 🏓")

@bot.tree.command(name="hello", description="Greets the user")
async def slash_hello(interaction: discord.Interaction):
    """Slash command that greets the user"""
    await interaction.response.send_message(f"Hello there, {interaction.user.mention}!")

@bot.tree.command(name="echo", description="Repeats your message")
@app_commands.describe(message="The message to repeat")
async def slash_echo(interaction: discord.Interaction, message: str):
    """Slash command that echoes a message"""
    await interaction.response.send_message(f"You said: {message}")

class RPSGame(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member = None):
        super().__init__(timeout=120)
        self.player1 = player1
        self.player2 = player2
        self.moves = {}
    
    async def process_move(self, interaction: discord.Interaction, choice: str):
        user = interaction.user
        
        # Assign player 2 if playing open game
        if self.player2 is None and user != self.player1:
            self.player2 = user
        
        # Check if user is a participant
        if user not in [self.player1, self.player2]:
            await interaction.response.send_message("You are not part of this game!", ephemeral=True)
            return

        # Check if already moved
        if user.id in self.moves:
            await interaction.response.send_message("You already chose your move!", ephemeral=True)
            return
            
        self.moves[user.id] = choice
        await interaction.response.send_message(f"You chose **{choice}**.", ephemeral=True)
        
        # Check if game needs to wait for second player
        if self.player2 is None:
             # Just waiting for player 2 
             return

        # Check if both players have moved
        if len(self.moves) == 2:
            await self.end_game(interaction)

    async def end_game(self, interaction: discord.Interaction):
        p1_move = self.moves[self.player1.id]
        p2_move = self.moves[self.player2.id]
        
        result = self.get_result(p1_move, p2_move)
        
        content = f"**Game Over!**\n{self.player1.mention} chose **{p1_move}**\n{self.player2.mention} chose **{p2_move}**\n\n**{result}**"
        
        for child in self.children:
            child.disabled = True
            
        await interaction.message.edit(content=content, view=self)
        self.stop()

    def get_result(self, p1, p2):
        if p1 == p2:
            return "It's a tie! 🤝"
        wins = {'rock': 'scissors', 'paper': 'rock', 'scissors': 'paper'}
        if wins[p1] == p2:
            return f"{self.player1.mention} wins! 🎉"
        return f"{self.player2.mention} wins! 🎉"

    @discord.ui.button(label="Rock", style=discord.ButtonStyle.primary, emoji="🪨")
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, "rock")

    @discord.ui.button(label="Paper", style=discord.ButtonStyle.primary, emoji="📄")
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, "paper")
        
    @discord.ui.button(label="Scissors", style=discord.ButtonStyle.primary, emoji="✂️")
    async def scissors(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_move(interaction, "scissors")

@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors with another user")
@app_commands.describe(opponent="The user you want to challenge (optional)")
async def slash_rps(interaction: discord.Interaction, opponent: discord.Member = None):
    """Play a game of Rock, Paper, Scissors"""
    
    if opponent and opponent.id == interaction.user.id:
         await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)
         return
    
    if opponent and opponent.bot:
         await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
         return

    view = RPSGame(player1=interaction.user, player2=opponent)
    msg_content = f"**Rock Paper Scissors!** 🪨📄✂️\n{interaction.user.mention} wants to play!"
    if opponent:
        msg_content += f"\nChallenge to {opponent.mention}!"
    else:
        msg_content += "\nWaiting for an opponent to join..."
        
    await interaction.response.send_message(msg_content, view=view)

if __name__ == '__main__':
    if not TOKEN or TOKEN == 'YOUR_BOT_TOKEN_HERE':
        print("Error: Please add your actual Discord bot token to the .env file.")
        print("Example in .env: DISCORD_TOKEN=your_token_here")
    else:
        try:
            from keep_alive import keep_alive
            keep_alive()
            bot.run(TOKEN)
        except discord.errors.LoginFailure:
            print("Error: Invalid token. Please check your token and try again.")
