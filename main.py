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

class TicTacToeButton(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction):
        view: TicTacToeView = self.view
        await view.process_move(interaction, self)

class TicTacToeView(discord.ui.View):
    def __init__(self, player1: discord.Member, player2: discord.Member = None):
        super().__init__(timeout=180)
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[0, 0, 0], [0, 0, 0], [0, 0, 0]] # 0: Empty, 1: X (p1), 2: O (p2)
        
        # Add buttons
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    async def process_move(self, interaction: discord.Interaction, button: TicTacToeButton):
        user = interaction.user
        
        # Open game handling
        if self.player2 is None and user != self.player1:
            self.player2 = user
            
        if user not in [self.player1, self.player2]:
            await interaction.response.send_message("You are not part of this game!", ephemeral=True)
            return
            
        if user != self.current_player:
            await interaction.response.send_message("It's not your turn!", ephemeral=True)
            return
            
        # Board update
        value = 1 if user == self.player1 else 2
        self.board[button.y][button.x] = value
        
        # Update button visual
        button.style = discord.ButtonStyle.primary if value == 1 else discord.ButtonStyle.danger
        button.label = "X" if value == 1 else "O"
        button.disabled = True
        
        # Check win
        winner = self.check_winner()
        if winner:
            await self.end_game(interaction, winner)
            return
            
        # Check tie
        if all(cell != 0 for row in self.board for cell in row):
            await self.end_game(interaction, 0)
            return
            
        # Switch turn
        self.current_player = self.player2 if self.current_player == self.player1 else self.player1
        
        msg = f"**Tic Tac Toe!**\n{self.player1.mention} (X) vs {self.player2.mention if self.player2 else 'Waiting...'} (O)"
        msg += f"\nIt's {self.current_player.mention}'s turn!" if self.player2 else "\nWaiting for opponent..."
        
        await interaction.response.edit_message(content=msg, view=self)

    def check_winner(self):
        # Rows, Cols
        for i in range(3):
            if self.board[i][0] == self.board[i][1] == self.board[i][2] != 0: return self.board[i][0]
            if self.board[0][i] == self.board[1][i] == self.board[2][i] != 0: return self.board[0][i]
            
        # Diagonals
        if self.board[0][0] == self.board[1][1] == self.board[2][2] != 0: return self.board[0][0]
        if self.board[0][2] == self.board[1][1] == self.board[2][0] != 0: return self.board[0][2]
        
        return None

    async def end_game(self, interaction: discord.Interaction, winner):
        for child in self.children:
            child.disabled = True
            
        if winner == 0:
            content = f"**It's a Tie!**\n{self.player1.mention} vs {self.player2.mention}"
        elif winner == 1:
            content = f"**{self.player1.mention} (X) Wins!** 🎉"
        else:
            content = f"**{self.player2.mention} (O) Wins!** 🎉"
            
        await interaction.response.edit_message(content=content, view=self)
        self.stop()

@bot.tree.command(name="tictactoe", description="Play Tic Tac Toe")
@app_commands.describe(opponent="The user to play against (optional)")
async def slash_tictactoe(interaction: discord.Interaction, opponent: discord.Member = None):
    """Play Tic Tac Toe"""
    if opponent and opponent.id == interaction.user.id:
        await interaction.response.send_message("You cannot play against yourself!", ephemeral=True)
        return
    if opponent and opponent.bot:
        await interaction.response.send_message("You cannot play against a bot!", ephemeral=True)
        return
        
    view = TicTacToeView(player1=interaction.user, player2=opponent)
    msg = f"**Tic Tac Toe!**\n{interaction.user.mention} (X) has started a game!"
    if opponent:
        msg += f"\nChallenge to {opponent.mention} (O)!"
    else:
        msg += "\nWaiting for an opponent to join..."
        
    await interaction.response.send_message(msg, view=view)

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
