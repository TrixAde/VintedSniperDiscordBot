import discord
from discord.ext import commands
import urllib.parse
from pyVinted import Vinted
from discord import app_commands
import json
import requests
import asyncio
import time

intents = discord.Intents.default()
intents.message_content = True

client = commands.Bot(command_prefix='!', intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')

vinted = Vinted()

user = ""
webhook_url = "" # remplace avec ton webhook
mini, maxi = 2, 40

search_terms = []
search_task = None
snipe_running = False

def currency(curr: str):
    return {"EUR": "€", "USD": "$"}[curr] or curr

def price(p):
    return int(p) if p % 1 == 0 else p

def embed(image: str = None, **kwargs):
    return {**kwargs, "thumbnail": {"url": image}}

def field(name: str, value: str, **kwargs):
    return {**kwargs, "name": name, "value": value}

async def get_new_items(delay):
    global search_task
    search_task = True

    last_items = []

    while search_task:
        for search_term in search_terms:
            search_url = f"https://www.vinted.fr/catalog?search_text={urllib.parse.quote(search_term)}&order=newest_first&price_from={mini}&price_to={maxi}"

            items = vinted.items.search(search_url, 5)

            if len(items) == 0:
                continue

            new_item = items[0]

            if new_item.id not in last_items and abs(new_item.created_at_ts.timestamp() - time.time()) < 60:
                real_price = price(float(new_item.price))
                service_fee = price(float(new_item.raw_data["service_fee"]))
                pay_price = price(round(real_price + service_fee))
                cur = currency(new_item.currency)

                color = eval("0x" + new_item.raw_data["photo"]["dominant_color"][1:]) if new_item.raw_data["photo"] and new_item.raw_data["photo"]["dominant_color"] else None

                data = {
                    "content": user.mention,
                    "avatar_url": "https://media.discordapp.net/attachments/626438212230840340/1125078726519050350/ViSniper.png",
                    "embeds": [
                        embed(
                            title=new_item.title,
                            color=color,
                            image=new_item.photo,
                            footer={"text": f"Identifiant du produit : {new_item.id}"},
                            fields=[
                                field("💵 Prix", f"{real_price} {cur} | **{pay_price} {cur} TTC**"),
                                field("🙋 Vendeur", "[" + new_item.raw_data["user"]["login"] + "](" + new_item.raw_data["user"]["profile_url"] + ")", inline=True),
                                field("👕 Marque", new_item.brand_title or "*Non spécifiée*", inline=True),
                                field("📏 Taille", new_item.size_title or "*Non spécifiée*", inline=True),
                                field("⏳ Depuis", f"<t:{int(new_item.created_at_ts.timestamp())}:R>", inline=True),
                                field("🔗 Lien", f"[Ouvrir]({new_item.url})"),
                            ]
                        )
                    ]
                }

                requests.post(webhook_url, data=json.dumps(data), headers={"Content-Type": "application/json"})

                last_items.append(new_item.id)

        await asyncio.sleep(delay)

@client.tree.command(description='Clique ici pour pouvoir Snipe un produit')
@app_commands.describe(article="Entre le nom du produit à rechercher", min="Valeur minimale du prix", max="Valeur maximale du prix")
async def snipe(interaction: discord.Interaction, article: str, min: int, max: int):
    global snipe_running
    global user
    global mini, maxi

    user = interaction.user
    mini, maxi = min, max

    if snipe_running:
        await interaction.response.send_message("Le Snipe est déjà en cours.")
        return

    terms = [term.strip() for term in article.split(",") if term.strip() and len(term.strip()) > 1]

    global txt
    if len(terms) > 1:
        txt = "les termes"
    else:
        txt = "le terme"

    await interaction.response.send_message(f"Snipe lancé avec {txt} : **__{terms}__** et une fourchette de prix de **__{min} à {max}€__**")
    search_terms.extend(terms)
    snipe_running = True
    await get_new_items(4)

@client.tree.command(description='Stop ici le Snipe')
async def stop(interaction: discord.Interaction):
    global snipe_running
    global search_task

    if not snipe_running:
        await interaction.response.send_message("Le Snipe n'est pas en cours.")
        return

    snipe_running = False
    search_task = False
    await interaction.response.send_message("Le Snipe est désormais stoppé")

client.run('') # remplace avec le token de ton bot
