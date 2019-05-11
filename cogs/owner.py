import discord
from discord.ext import commands
import datetime
from contextlib import redirect_stdout
import textwrap
import io
import traceback
import asyncio
import re
import inspect
import sys
sys.path.append("../")
import config # Note: Only importing config module since it's easier to use in eval


SUPPORT_GUILD = 499357399690379264
SUPPOR_GUILD_AUTH_ROLE = 531176653184040961

class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cmdauthcheck(ctx): # pylint: disable=E0213
        guild = ctx.bot.get_guild(SUPPORT_GUILD)
        role = guild.get_role(SUPPOR_GUILD_AUTH_ROLE)
        user = guild.get_member(ctx.author.id) # pylint: disable=E1101
        try:
            if role in user.roles:
                return True
            else:
                return False
        except AttributeError:
            return False

    @commands.command()
    @commands.check(cmdauthcheck)
    async def authorize(self, ctx, g: int = None):
        if g != None:
            guild = self.bot.get_guild(g)
            if guild == None:
                em = discord.Embed(color = discord.Color.dark_teal())
                em.add_field(name = "Guild Not Found", value = f"The guild (`{g}`) couldn't be found.")
                await ctx.send(embed = em)
                return
        else:
            guild = ctx.guild

        gchck = await self.bot.pool.fetchrow("SELECT * FROM authorized WHERE guildid = $1", guild.id)
        if gchck != None:
            emb = discord.Embed(color = discord.Color.dark_teal())
            emb.add_field(name = "Already Authorized", value = f"`{guild.name}` is already authorized")
            await ctx.send(embed = emb)
            return

        await self.bot.pool.execute("INSERT INTO authorized VALUES ($1)", guild.id)

        em = discord.Embed(color = discord.Color.dark_purple())
        em.add_field(name = "Authorized", value = f"`{guild.name}` has been authorized")
        await ctx.send(embed = em)

    @commands.command()
    @commands.check(cmdauthcheck)
    async def deauthorize(self, ctx, g: int = None):
        if g != None:
            guild = self.bot.get_guild(g)
            if guild == None:
                em = discord.Embed(color = discord.Color.dark_teal())
                em.add_field(name = "Guild Not Found", value = f"The guild (`{g}`) couldn't be found.")
                await ctx.send(embed = em)
                return
        else:
            guild = ctx.guild

        gchck = await self.bot.pool.fetchrow("SELECT * FROM authorized WHERE guildid = $1", guild.id)
        if gchck == None:
            emb = discord.Embed(color = discord.Color.dark_teal())
            emb.add_field(name = "Never Authorized", value = f"`{guild.name}` was never authorized")
            await ctx.send(embed = emb)
            return

        await self.bot.pool.execute("DELETE FROM authorized WHERE guildid = $1", guild.id)

        em = discord.Embed(color = discord.Color.dark_purple())
        em.add_field(name = "Deauthorized", value = f"`{guild.name}` has been deauthorized")
        await ctx.send(embed = em)

    @commands.command()
    @commands.is_owner()
    async def update(self, ctx):
        pro = await asyncio.create_subprocess_exec(
            "git", "pull",
            stdout = asyncio.subprocess.PIPE,
            stderr = asyncio.subprocess.PIPE
        )

        try:
            com = await asyncio.wait_for(pro.communicate(), timeout = 10)
            com = com[0].decode() + "\n" + com[1].decode()
        except asyncio.TimeoutError:
            await ctx.send("Took too long to respond")
            return

        reg = r"(.*?)\.py"
        found = re.findall(reg, com)

        if found:
            updated = []
            final_string = ""

            for x in found:
                extension = re.sub(r"\s+", "", x)
                extension = extension.replace("/", ".")

                try:
                    self.bot.reload_extension(extension)
                except ModuleNotFoundError:
                    continue
                except Exception as error:
                    if inspect.getfile(self.bot.__class__).replace(".py", "") in extension:
                        continue
                    else:
                        await ctx.send(f"Error: ```\n{error}\n```", delete_after = 5)
                        continue

                updated.append(extension)

            for b in updated:
                final_string += f"`{b}` "

            if updated == []:
                await ctx.send("No cogs were updated")
            else:
                await ctx.send(f"Updated cogs: {final_string}")
        else:
            await ctx.send("No cogs were updated")

    @commands.command()
    @commands.is_owner()
    async def redis(self, ctx, *args):
        try:
            cmd = await self.bot.redis.execute(*args)
            await ctx.send(getattr(cmd, "decode", cmd.__str__)())
        except Exception as e:
            await ctx.send(e)

    @commands.command(name = "eval")
    @commands.is_owner()
    async def ev(self, ctx, *, code: str):
        """From R. Danny. I did not make this command"""
        env = {
            "bot": self.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message
        }

        env.update(globals())
        stdout = io.StringIO()
        to_compile = f"async def func():\n{textwrap.indent(code, '  ')}"

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f"```py\n{e.__class__.__name__}: {e}\n```")

        func = env["func"]

        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f"```py\n{value}{traceback.format_exc()}\n```")
        else:
            value = stdout.getvalue()
            if ret is None:
                if value:
                    await ctx.send(f"```py\n{value}\n```")
            else:
                _last_result = ret
                await ctx.send(f"```py\n{value}{ret}\n```")


def setup(bot):
    bot.add_cog(Owner(bot))