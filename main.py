import discord
from discord import app_commands
import re
import os
import asyncio
import resend

# Set your Resend API key from environment variables
resend.api_key = os.getenv('RESEND_API_KEY')

import json


# Function to load JSON data from a file
def load_json_file(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)


# Load JSON data from file
file_path = 'employee.json'
employees = load_json_file(file_path)["employees"]


# Function to search for employee by ID or Discord User ID
def get_employee_details(employee_id=None, discord_user_id=None):
    for employee in employees:
        if employee_id is not None and employee["id"] == employee_id:
            return employee["name"], employee["full_name"]
        if discord_user_id is not None and employee[
                "discord_user_id"] == discord_user_id:
            return employee["name"], employee["full_name"]
    return None, None


# Discord Client


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
    email = discord.ui.TextInput(label="Email Address",
                                 style=discord.TextStyle.short,
                                 required=True)
    subject = discord.ui.TextInput(label="Subject",
                                   style=discord.TextStyle.short,
                                   required=True)
    body = discord.ui.TextInput(label="Body",
                                style=discord.TextStyle.paragraph,
                                required=True)
    file_name = discord.ui.TextInput(label="File Name",
                                     style=discord.TextStyle.short,
                                     required=False)

    async def on_submit(self, interaction: discord.Interaction):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, self.email.value):
            await interaction.response.send_message("Invalid email address.",
                                                    ephemeral=True)
            return

        attachment_info = ""
        attachments = []
        if self.file_name.value:
            # Check the last few messages from the user for attachments
            channel = interaction.channel
            found = False
            async for message in channel.history(limit=20):
                if message.author == interaction.user:
                    for attachment in message.attachments:
                        if attachment.filename == self.file_name.value:
                            f = await attachment.read()
                            attachments.append({
                                "filename": attachment.filename,
                                "content": list(f)
                            })
                            attachment_info = f"\nAttachment: {attachment.filename} ({attachment.size} bytes)"
                            found = True
                            break
                if found:
                    break

            if not found:
                await interaction.response.send_message(
                    "Error: File not found. Email request canceled.",
                    ephemeral=True)
                return

        user_name = interaction.user.name
        # Send email using Resend API
        params = {
            "from":
            f"{get_employee_details(discord_user_id=user_name)[0]}@mail.quadropic.com",
            "to": [self.email.value],
            "subject": self.subject.value,
            "html": f"""<strong>{self.body.value}</strong><br><br>Regards,
            {get_employee_details(discord_user_id=user_name)
            [1]} from Quadropic""",
            "attachments": attachments
        }

        try:
            email_response = resend.Emails.send(params)
            await interaction.response.send_message(
                f"Email sent successfully to {self.email.value}.\nSubject: {self.subject.value}\nBody: {self.body.value}{attachment_info}"
            )
        except Exception as e:
            await interaction.response.send_message(
                f"Error sending email: {str(e)}", ephemeral=True)


@client.tree.command(name="send_email",
                     description="Send an email with subject and body")
async def send_email(interaction: discord.Interaction):
    await interaction.response.send_modal(EmailModal())


async def main():
    async with client:
        await client.start(os.getenv('DISCORD_BOT_TOKEN'))


if __name__ == "__main__":
    asyncio.run(main())
