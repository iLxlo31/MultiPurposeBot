import discord
from discord.ext import commands, tasks
import configparser
import re
import asyncio
from discord.ui import View, Button

config_path = "./data/config.ini"
file = discord.File("./images/6529981ee3bfdc6d2c1b1d66ce5bd.jpg")


class DeleteCog(commands.Cog):
    def __init__(self, client):
        self.config = configparser.ConfigParser()
        self.config.read("./data/config.ini")
        self.client = client
        self.delete_task.start()
        self.auth_url = self.config["Auth"]["url"]

    def cog_unload(self):
        self.delete_task.cancel()

    def is_valid_timeout(self, timeout):
        return re.match(r'^(\d+[hms])+$', timeout)

    async def delete_messages(self, channel):
        def is_not_pinned(message):
            return not message.pinned

        messages_to_delete = await channel.purge(limit=None, check=is_not_pinned)

        return messages_to_delete

    @tasks.loop(seconds=10)
    async def delete_task(self):
        config = configparser.ConfigParser()
        config.read(config_path)
        timeout_str = config.get("DeleteTimeout", "timeout")

        if timeout_str:
            timeout = self.parse_timeout(timeout_str)
            channel_id = config.get("Discord", "channel", fallback="0")
            if channel_id.isdigit():
                channel = self.client.get_channel(int(channel_id))
                if channel:
                    try:
                        messages_to_delete = await self.delete_messages(channel)

                        if messages_to_delete:
                            await asyncio.sleep(2)

                            await channel.delete_messages(messages_to_delete)
                            view = discord.ui.View()
                            button = discord.ui.Button(
                                label="Verify to see more", url=self.auth_url, style=discord.ButtonStyle.link
                            )
                            view.add_item(button)
                            embed = discord.Embed(
                                title="Posting New Images",
                                description="Fetching new images!",
                                color=0x2F3136
                            )
                            embed.set_image(url=f"attachment://{file.filename}")
                            await channel.send(embed=embed, view=view)
                    except discord.errors.NotFound as e:
                        print(f"Error deleting messages: {e}")
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                else:
                    print("Channel not found.")
            else:
                print("Invalid channel ID in the config file.")

    def parse_timeout(self, timeout_str):
        total_seconds = 0
        matches = re.finditer(r'(\d+)([hms])', timeout_str)
        for match in matches:
            value, unit = int(match.group(1)), match.group(2)
            if unit == 'h':
                total_seconds += value * 3600
            elif unit == 'm':
                total_seconds += value * 60
            elif unit == 's':
                total_seconds += value
        return total_seconds

    @commands.command()
    async def setdeletetimeout(self, ctx, timeout: str):
        if not self.is_valid_timeout(timeout):
            embed = discord.Embed(
                title="Invalid Timeout Format",
                description="Invalid timeout format. Please use '1h', '10m', '1s', etc.",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        config = configparser.ConfigParser()
        config.read(config_path)
        if "DeleteTimeout" not in config:
            config["DeleteTimeout"] = {}

        config["DeleteTimeout"]["timeout"] = timeout
        self.delete_task.change_interval(seconds=self.parse_timeout(timeout))

        with open(config_path, "w") as config_file:
            config.write(config_file)

        embed = discord.Embed(
            title="Delete Timeout Updated",
            description=f"Delete timeout set to {timeout}. The automatic delete interval has been updated.",
            color=0x2F3136
        )
        await ctx.send(embed=embed)

async def setup(client):
    await client.add_cog(DeleteCog(client))
