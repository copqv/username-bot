import discord
from discord import app_commands
import random
import asyncio
import time
import os

TOKEN = os.getenv("TOKEN") or ""

# ===== ACCESS CONTROL =====
ALLOWED_ROLE_ID = 1500957593143607366
OWNER_ID = 632993587994296323

# ===== EMOJIS =====
E_TITLE = "<a:emojigg_1:1500952766649073868>"
E_SCAN = "<a:Loading:1499558187714478232>"
E_HIT = "<:34870lightbluefire:1498789084553019524>"
E_BEST = "<:Red_Neon_Owner_Crown:1495539123208061068>"
E_COPY = "<:CopyPaste:1500952000836407517>"
E_REFRESH = "<:Modern_Refresh:1500952261084319784>"
E_SAVE = "<:Save:1500952389442732082>"
E_LOCK = "<:locked:1500952556594266234>"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

cooldowns = {}
saved_data = {}
recent_names = set()

# ===== CHARACTER POOLS =====
rare = "qxzjkv"
semi = "bcdfghlmnrst"
numbers = "0123456789"
vowels = "aeiou"

# ===== FILTER =====
def is_bad(name):
    return name.isdigit() or len(set(name)) <= 2

# ===== SCORE =====
def score(name):
    s = 0
    for c in name:
        if c in rare:
            s += 3
        elif c in semi:
            s += 1.5
        elif c.isdigit():
            s += 2
        else:
            s += 0.5

    if sum(1 for c in name if c in vowels) >= 2:
        s -= 5
    if any(c.isdigit() for c in name) and any(c.isalpha() for c in name):
        s += 2
    if name.isalpha():
        s -= 4
    if len(set(name)) <= 2:
        s -= 3
    if name in ["abcd", "1234", "qwer"]:
        s -= 6

    return s

# ===== GENERATION =====
def generate_name():
    name = ""
    for _ in range(4):
        r = random.random()
        if r < 0.4:
            pool = rare
        elif r < 0.8:
            pool = semi
        else:
            pool = numbers
        name += random.choice(pool)
    return name

def generate_best():
    global recent_names

    candidates = set()
    attempts = 0

    while len(candidates) < 80 and attempts < 500:
        n = generate_name()
        if not is_bad(n) and n not in recent_names:
            candidates.add(n)
        attempts += 1

    recent_names.update(candidates)

    if len(recent_names) > 300:
        recent_names = set(list(recent_names)[-150:])

    ranked = sorted(candidates, key=score, reverse=True)
    return ranked[:7]

# ===== CONFIDENCE =====
def build_confidence(names):
    result = []
    for i, n in enumerate(names):
        s = score(n)

        if i == 0:
            label = "<a:tickgreen:1500959488302125106> Low Risk"
        elif s >= 7:
            label = "<a:tickred:1500959621689643089> Medium Risk"
        else:
            label = "🔴 High Risk"

        result.append((n, label))

    return result

# ===== EMBED =====
def build_embed(stage, user, names=None, shown=None):
    color = discord.Color.from_rgb(90, 0, 200)

    if stage == "scan":
        desc = f"{E_SCAN} **Scanning engine...**\n\nResults: `{len(shown) if shown else 0}`"
    else:
        data = build_confidence(names)
        best = data[0]
        others = data[1:]

        desc = f"{E_BEST} **BEST PICK**\n`{best[0]}` • {best[1]}\n\n"
        desc += "━━━━━━━━━━━━━━\n**CANDIDATES**\n"

        for n, c in others:
            desc += f"{E_HIT} `{n}` • {c}\n"

        desc += f"\n{E_COPY} `{' '.join(names)}`"

    embed = discord.Embed(
        title=f"{E_TITLE} Cop 4L Sniper Engine",
        description=desc,
        color=color
    )

    embed.set_footer(text="Developed by cop! .gg/copqv")
    embed.timestamp = discord.utils.utcnow()

    return embed

# ===== SAVED VIEW =====
class SavedView(discord.ui.View):
    def __init__(self, owner_id):
        super().__init__(timeout=60)
        self.owner_id = owner_id

    async def interaction_check(self, interaction):
        return interaction.user.id == self.owner_id

    @discord.ui.button(label="Reset Saved", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def reset(self, interaction, button):
        saved_data[self.owner_id] = []
        await interaction.response.edit_message(
            content="Your saved usernames have been cleared.",
            embed=None,
            view=None
        )

# ===== BUTTON VIEW =====
class View(discord.ui.View):
    def __init__(self, owner):
        super().__init__(timeout=120)
        self.owner = owner

    async def interaction_check(self, interaction):
        return interaction.user.id == self.owner

    @discord.ui.button(label="Resnipe", style=discord.ButtonStyle.primary, emoji=E_REFRESH)
    async def regen(self, interaction, button):
        await run(interaction, edit=True)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.success, emoji=E_SAVE)
    async def save(self, interaction, button):
        embed = interaction.message.embeds[0]
        names = [x.strip("`") for x in embed.description.split() if len(x.strip("`")) == 4]

        uid = interaction.user.id
        if uid not in saved_data:
            saved_data[uid] = []

        saved_data[uid].extend(names)

        await interaction.response.send_message(
            f"Saved {len(names)} usernames.",
            ephemeral=True
        )

    @discord.ui.button(label="Private", style=discord.ButtonStyle.secondary, emoji=E_LOCK)
    async def private(self, interaction, button):
        await run(interaction, ephemeral=True)

# ===== ENGINE =====
async def run(interaction, edit=False, ephemeral=False):
    names = generate_best()
    shown = []

    if edit:
        await interaction.response.defer()
        msg = await interaction.original_response()
    else:
        await interaction.response.send_message(
            embed=build_embed("scan", interaction.user, shown=shown),
            ephemeral=ephemeral
        )
        msg = await interaction.original_response()

    try:
        for n in names:
            await asyncio.sleep(0.25)
            shown.append(n)
            await msg.edit(embed=build_embed("scan", interaction.user, shown=shown))

        await asyncio.sleep(0.2)

        final = build_embed("done", interaction.user, names=names)
        await msg.edit(embed=final, view=View(interaction.user.id))

    except Exception as e:
        print("ERROR:", e)

# ===== COMMANDS =====
@tree.command(name="user", description="4L username sniper")
async def user(interaction: discord.Interaction):
    uid = interaction.user.id

    if interaction.user.id != OWNER_ID:
        if not any(role.id == ALLOWED_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(
                "You don't have access to this tool.",
                ephemeral=True
            )

    if uid in cooldowns and time.time() - cooldowns[uid] < 3:
        return await interaction.response.send_message("Slow down.", ephemeral=True)

    cooldowns[uid] = time.time()
    await run(interaction)

@tree.command(name="saved", description="View your saved usernames")
async def saved(interaction: discord.Interaction):
    uid = interaction.user.id
    data = saved_data.get(uid, [])

    if not data:
        return await interaction.response.send_message(
            "You have no saved usernames.",
            ephemeral=True
        )

    display = data[-50:]

    embed = discord.Embed(
        title="📂 Your Saved Usernames",
        description=f"```{' '.join(display)}```",
        color=discord.Color.from_rgb(90, 0, 200)
    )

    embed.set_footer(text=f"Total saved: {len(data)}")

    await interaction.response.send_message(
        embed=embed,
        view=SavedView(uid),
        ephemeral=True
    )

# ===== READY =====
@client.event
async def on_ready():
    await tree.sync()
    print(f"Logged in as {client.user}")

client.run(TOKEN)