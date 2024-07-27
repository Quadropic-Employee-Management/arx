import discord
from discord import app_commands
import re
import os
import asyncio

class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

client = MyClient()

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')

class EmailModal(discord.ui.Modal, title="Email Details"):
    email = discord.ui.TextInput(label="Email Address", style=discord.TextStyle.short, required=True)
    subject = discord.ui.TextInput(label="Subject", style=discord.TextStyle.short, required=True)
    body = discord.ui.TextInput(label="Body", style=discord.TextStyle.paragraph, required=True)
    file_name = discord.ui.TextInput(label="File Name", style=discord.TextStyle.short, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, self.email.value):
            await interaction.response.send_message("Invalid email address.", ephemeral=True)
            return

        attachment_info = ""
        if self.file_name.value:
            # Check the last few messages from the user for attachments
            channel = interaction.channel
            found = False
            async for message in channel.history(limit=20):
                if message.author == interaction.user:
                    for attachment in message.attachments:
                        if attachment.filename == self.file_name.value:
                            attachment_info = f"\nAttachment: {attachment.filename} ({attachment.size} bytes)"
                            found = True
                            break
                if found:
                    break

            if not found:
                await interaction.response.send_message("Error: File not found. Email request canceled.", ephemeral=True)
                return

        # Here, you would add your email sending logic
        # For now, we just echo back the details
        await interaction.response.send_message(
            f"Email: {self.email.value}\nSubject: {self.subject.value}\nBody: {self.body.value}{attachment_info}"
        )

@client.tree.command(name="send_email", description="Send an email with subject and body")
async def send_email(interaction: discord.Interaction):
    await interaction.response.send_modal(EmailModal())

async def main():
    async with client:
        await client.start(os.getenv('DISCORD_BOT_TOKEN'))

if __name__ == "__main__":
    asyncio.run(main())
