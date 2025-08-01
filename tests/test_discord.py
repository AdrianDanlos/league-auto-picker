import requests

webhook_url = "https://discord.com/api/webhooks/1400894060276748448/qflPvLqhtoymtnU4o9br3grXkV4HJIl2WYtTAY6BQ2__D5MyAbZqpv-FsW3lEKjPcAN2"

# Mensaje que quieres enviar
mensaje = (
    f"```ansi\n"
    f"\u001b[1;32m🎮 ═══ GAME STARTED ═══ 🎮\u001b[0m\n"
    f"```\n"
    f"👤 **Player:** `N3 Machine`\n"
    f"⚔️ **Champion:** `Kled`\n"
    f"🛡️ **Role:** `Top Lane`\n\n"
    f"🏆 **Good luck and have fun!** 🏆\n"
    "🌍 **Porofessor:** <https://porofessor.gg/live/euw/n3%20essential-0000>"
)

data = {"content": mensaje}

response = requests.post(webhook_url, json=data)

if response.status_code == 204:
    print("✅ Mensaje enviado con éxito")
else:
    print(f"❌ Error al enviar mensaje: {response.status_code}")
    print(f"❌ Error al enviar mensaje: {response.text}")
