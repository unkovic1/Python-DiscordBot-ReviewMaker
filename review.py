import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio

# Učitavanje tokena
load_dotenv("token.env")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

# Kreiranje bota
intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="/", intents=intents)


@bot.event
async def on_ready():
    print(f'✅ Bot je aktivan kao {bot.user}')
    try:
        # Sync svih komandi sa Discord serverom
        bot.tree.clear_commands(guild=None)  # Opciono brisanje starih komandi pre sync-a
        bot.tree.add_command(reviewbrisi)
        bot.tree.add_command(review)
        bot.tree.add_command(rbrisisve)
        bot.tree.add_command(reviewhelp)
        synced = await bot.tree.sync()
        print(f"📌 Syncovano {len(synced)} komandi!")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="⭐ | /reviewhelp"))
    except Exception as e:
        print(f"❌ Greška prilikom sync-a: {e}")


#BRISI KOMANDA
# Slash komanda za brisanje review-a
@bot.tree.command(name="reviewbrisi", description="Obriši određeni review korisnika.")
@app_commands.describe(username="Discord korisničko ime (bez @)", broj="Redni broj review-a koji želite obrisati (1 = prvi, 2 = drugi, ...)")
async def reviewbrisi(interaction: discord.Interaction, username: str, broj: int):
    await interaction.response.defer()  # Izbegavanje timeouta
    
    review_channel = discord.utils.get(interaction.guild.text_channels, name="randomac-review")
    
    if not review_channel:
        await interaction.followup.send("❌ Kanal `randomac-review` ne postoji!", ephemeral=True)
        return

    reviews = []
    async for message in review_channel.history(limit=1000):  
        if message.author == bot.user and message.embeds:
            embed = message.embeds[0]
            if embed.footer and username in embed.footer.text:
                reviews.append(message)  # Čuvamo sve review-e korisnika

    if not reviews:
        await interaction.followup.send(f"⚠️ Nije pronađen nijedan review za korisnika **{username}**.", ephemeral=True)
        return

    reviews.reverse()  # Preokrećemo listu da bude u hronološkom redu (od prvog do poslednjeg)

    if broj < 1 or broj > len(reviews):
        await interaction.followup.send(f"⚠️ Korisnik **{username}** ima samo {len(reviews)} review-a. Unesite broj između 1 i {len(reviews)}.", ephemeral=True)
        return

    try:
        await reviews[broj - 1].delete()
        await interaction.followup.send(f"✅ {broj}. review korisnika **{username}** je uspešno obrisan!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Greška pri brisanju: {e}", ephemeral=True)

    
        
        
#BRISI SVE RECENZIJE KOMANDA
@bot.tree.command(name="rbrisisve", description="Obriši svaki review na osnovu korisničkog imena.")
@app_commands.describe(username="Discord korisničko ime (bez #tag-a)")
async def rbrisisve(interaction: discord.Interaction, username: str):
    await interaction.response.defer()  # Izbegavanje timeouta
    
    review_channel = discord.utils.get(interaction.guild.text_channels, name="randomac-review")
    
    if not review_channel:
        await interaction.followup.send("❌ Kanal `randomac-review` ne postoji!", ephemeral=True)
        return

    deleted = False
    async for message in review_channel.history(limit=1000):  
        if message.author == bot.user and message.embeds:
            embed = message.embeds[0]  # Uzimamo embed iz poruke
            if embed.footer and embed.footer.text.endswith(username):
                try:
                    await message.delete()
                    deleted = True
                
                except Exception as e:
                    await interaction.followup.send(f"❌ Greška pri brisanju: {e}", ephemeral=True)
                    return


    if deleted:
        await interaction.followup.send(f"✅ Svaki Review od **{username}** je uspešno obrisan!", ephemeral=True)
    else:
        await interaction.followup.send(f"⚠️ Nije pronađen ni jedan review za korisnika **{username}**.", ephemeral=True)   
        
        
        
        
         
#POMAGALO ZA KOMANDE
async def get_or_create_channel(guild, channel_name):
    """ Pronalaženje ili kreiranje kanala """
    channel = discord.utils.get(guild.text_channels, name=channel_name)
    if not channel:
        channel = await guild.create_text_channel(channel_name)
        print(f"✅ Kreiran kanal: {channel_name}")
        
        # Postavljanje informativne embed poruke
        embed_message = discord.Embed(
            title="📌 Važna informacija!",
            description="**Ne brišite i nemojte preimenovati ovaj kanal jer je u njemu predviđeno da se pišu recenzije!**\n\n"
                        "**Brisanje/preimenovanje ovog kanala može pokvariti rad bot komandi!**",
            color=discord.Color.red()
        )
        await channel.send(embed=embed_message)
    return channel


#RECENZIJA KOMANDA
@bot.tree.command(name="review", description="Dodajte recenziju sa slikom")
@app_commands.describe(naslov="Naslov recenzije", opis="Opis recenzije", ocena="Ocena od 1 do 5")
async def review(interaction: discord.Interaction, naslov: str, opis: str, ocena: int):
    """ Kreira stilizovan review i osigurava da je sačuvan u kanalu 'randomac-review'. """

    if ocena < 1 or ocena > 5:
        embed = discord.Embed(title="❌ Greška!", description="Broj zvezdica mora biti između **1 i 5**!", color=discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)  # Ovim omogućavamo kasniji odgovor
    prompt_message = await interaction.followup.send("📸 Pošaljite sliku ili napišite `skip` ako ne želite sliku.", ephemeral=True)

    def check(m):
        return m.author == interaction.user and (m.attachments or m.content.lower() == "skip")

    image_url = None
    try:
        message = await bot.wait_for("message", check=check, timeout=30)

        if message.attachments:  
            slike_review_channel = await get_or_create_channel(interaction.guild, "slike-review")

            # Upload slike u kanal 'slike-review'
            image_file = await message.attachments[0].to_file()
            sent_message = await slike_review_channel.send(file=image_file)
            image_url = sent_message.attachments[0].url  # Uzimamo URL slike iz kanala
            
        await message.delete()  # Brišemo originalnu poruku korisnika

    except asyncio.TimeoutError:
        await interaction.followup.send("⏳ Niste poslali sliku na vreme. Nastavljam bez slike.", ephemeral=True)

    await prompt_message.delete()  # Brišemo početnu poruku sa instrukcijama

    # Kreiranje embed-a za recenziju
    embed = discord.Embed(
        title=f"🛍 **Recenzija: {naslov}**",
        description=f"📢 **Opis:**\n{opis}\n\n⭐ **Ocena:** {'⭐' * ocena}",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Recenziju napisao: {interaction.user.name}", icon_url=interaction.user.avatar.url)

    if image_url:
        embed.set_image(url=image_url)

    # Osiguravamo da se recenzija sačuva u kanalu "randomac-review"
    review_channel = await get_or_create_channel(interaction.guild, "randomac-review")
    await review_channel.send(embed=embed)

    await interaction.followup.send("✅ Vaša recenzija je uspešno sačuvana u **randomac-review**!", ephemeral=True)
    


#WELCOME PORUKA FUNKCIONALNOST
@bot.event
async def on_guild_join(guild):
    # Prvo uzimamo pozivnice servera
    invites = await guild.invites()

    for invite in invites:
        if invite.uses == 1:  # Ako je pozivnica korišćena samo jednom
            inviter = invite.inviter  # Osoba koja je pozvala bota
            try:
                # Pravimo isti embed kao za kanal dobrodošlice
                embed = discord.Embed(
                    title=f"👋 Hvala što ste dodali {bot.user.name}!",
                    description=f"Bot je uspešno došao na server **{guild.name}** 🚀\n\n"
                                "✅ **Koristite** `/review` **kako biste ocenili uslugu!**\n"
                                "❗ **Važno:** Ne brišite i nemojte preimenovati kanal `slike-review`, **u njemu će biti sačuvane slike!**",
                    color=discord.Color.blue()
                )
                embed.set_footer(text="Uživajte u korišćenju bota!", icon_url=bot.user.avatar.url)

                # Slanje poruke korisniku koji je pozvao bota
                await inviter.send(embed=embed)
                break  # Prestaćemo sa pretrazivanjem čim nađemo pozivaoca
            except Exception as e:
                print(f"Greška pri slanju poruke: {e}")

    # Pronaći kanal gde bot može da šalje poruke
    channel = next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
    if channel:
        embed = discord.Embed(
            title=f"👋 Hvala što ste dodali {bot.user.name}!",
            description=f"Bot je uspešno došao na server **{guild.name}** 🚀\n\n"
                        "✅ **Koristite** `/review` **kako biste ocenili uslugu!**\n"
                        "❗ **Važno:** Ne brišite i nemojte preimenovati kanal `slike-review`, **u njemu će biti sačuvane slike!**",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Uživajte u korišćenju bota!", icon_url=bot.user.avatar.url)
        await channel.send(embed=embed)
        
    
     # Kreiranje kanala ako ne postoje
        existing_channels = {channel.name for channel in guild.text_channels}
        channels_to_create = ["randomac-review", "slike-review"]

        # Embed poruka za nove kanale
        channel_embed = discord.Embed(
            title="📌 Važna informacija!",
            description="**Ne brišite i nemojte preimenovati ovaj kanal kako bi slike za review bile prikazane!**\n\n"
                        "**Brisanje/preimenovanje ovog kanala može pokvariti rad bot komandi!**",
            color=discord.Color.red()
        )
        
        channel_embed2 = discord.Embed(
            title="📌 Važna informacija!",
            description="**Ne brišite i nemojte preimenovati ovaj kanal jer je u njemu predviđeno da se pišu recenzije!**\n\n"
                        "**Brisanje/preimenovanje ovog kanala može pokvariti rad bot komandi!**",
            color=discord.Color.red()
        )

        for channel_name in channels_to_create:
            if channel_name not in existing_channels:
                try:
                    new_channel = await guild.create_text_channel(channel_name)

            # Proveravamo koji je kanal u pitanju i šaljemo odgovarajući embed
                    if channel_name == "randomac-review":
                        await new_channel.send(embed=channel_embed2)
                    elif channel_name == "slike-review":
                        await new_channel.send(embed=channel_embed)

                    print(f"✅ Kanal '{channel_name}' je kreiran u serveru '{guild.name}' i postavljena je embed poruka.")
                except Exception as e:
                    print(f"❌ Greška pri kreiranju kanala '{channel_name}': {e}")
                    
        
#HELP KOMANDA
@bot.tree.command(name="reviewhelp", description="Prikazuje sve dostupne komande za review sistem.")
async def reviewhelp(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 Review Bot - Komande",
        description="Lista svih dostupnih komandi za upravljanje recenzijama:",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📌 `/review`", value="Dodajte recenziju sa slikom.", inline=False)
    embed.add_field(name="🗑 `/reviewbrisi`", value="Obrišite recenziju na osnovu korisničkog imena.", inline=False)
    embed.add_field(name="🗑 `/rbrisisve`", value="Obrišite sve recenzije korisnika.", inline=False)
    
    embed.set_footer(text="Koristite ove komande za upravljanje recenzijama!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
        

# Pokretanje bota
bot.run(DISCORD_TOKEN)