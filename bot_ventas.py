import logging
import os
from math import ceil
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from fpdf import FPDF

# --- CONFIGURACIÓN ---
TOKEN = "7758364839:AAHi9mYo5rLfg8ODc6Cm2hSSiB_tBted3j8"

# RUTAS DE ARCHIVOS
# Usamos r"" para que lea bien las barras de Windows
LOGO_PATH = "logo.png"

# ESTADOS DE LA CONVERSACIÓN
SELECCIONAR_SERVICIO, INGRESAR_METROS, INGRESAR_LED = range(3)

# Configuración de log
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CLASE PARA GENERAR EL PDF ---
class PresupuestoPDF(FPDF):
    def header(self):
        # --- AQUÍ ESTÁ LA CORRECCIÓN DEL LOGO ---
        # Verificamos si el archivo existe y lo ponemos directo (sin try/except)
        # para ver si hay errores.
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, 10, 8, 33)
        else:
            print(f"⚠️ ADVERTENCIA: No encuentro el logo en: {LOGO_PATH}")
            
        self.set_font('Arial', 'B', 15)
        self.set_text_color(10, 26, 42) # Azul oscuro Asenso
        self.cell(80)
        self.cell(30, 10, 'ASENSO SOLUCIONES', 0, 0, 'C')
        self.ln(5)
        self.set_font('Arial', '', 10)
        self.cell(80)
        self.cell(30, 10, 'Alta Remodelación e Inteligencia Artificial', 0, 0, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-35)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 5, 'NOTA: Todos los precios están sujetos a cambios sin previo aviso.', 0, 1, 'C')
        self.cell(0, 5, 'Transformamos tus espacios con tecnología y pasión.', 0, 1, 'C')
        self.cell(0, 5, 'Caracas, Venezuela | Tel: 0412-301-5376', 0, 1, 'C')
        self.cell(0, 5, 'Presupuesto válido por 15 días.', 0, 0, 'C')

# --- FUNCIONES DEL BOT ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    usuario = update.effective_user.first_name
    mensaje = (
        f"👋 ¡Hola {usuario}! Bienvenido a **Asenso Soluciones**.\n\n"
        "Soy tu asistente de presupuestos. Selecciona un servicio para cotizar tu proyecto ahora mismo:"
    )
    botones = [
        [InlineKeyboardButton("🧱 Drywall (Techos/Paredes)", callback_data='drywall')],
        [InlineKeyboardButton("✨ Microcemento", callback_data='microcemento')],
        [InlineKeyboardButton("💧 Resina Epóxica", callback_data='resina')],
        [InlineKeyboardButton("👨‍🔧 Hablar con Diego", url='https://wa.me/584123015376')]
    ]
    if update.callback_query:
        await update.callback_query.message.edit_text(mensaje, reply_markup=InlineKeyboardMarkup(botones), parse_mode='Markdown')
    else:
        await update.message.reply_text(mensaje, reply_markup=InlineKeyboardMarkup(botones), parse_mode='Markdown')
    return SELECCIONAR_SERVICIO

async def pedir_metros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['servicio'] = query.data
    
    # Textos personalizados
    if query.data == 'drywall':
        texto = "🧱 **Proyecto Drywall**\n\nIndícame los metros cuadrados ($m^2$) del área (techo o pared).\n_Ejemplo: escribe 20_"
    elif query.data == 'microcemento':
        texto = "✨ **Proyecto Microcemento**\n\nIndícame los metros cuadrados ($m^2$) a cubrir.\n_Recuerda nuestra promo: Paredes de hasta 4m² tienen precio especial._"
    else:
        texto = "💧 **Proyecto Resina Epóxica**\n\nIndícame los metros cuadrados ($m^2$) del piso.\n_Nota: El precio asume piso listo para aplicar._"
        
    await query.message.edit_text(texto, parse_mode='Markdown')
    return INGRESAR_METROS

async def procesar_metros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not texto.isdigit():
        await update.message.reply_text("⚠️ Por favor escribe solo el número (ej: 15).")
        return INGRESAR_METROS
    
    metros = int(texto)
    context.user_data['metros'] = metros
    servicio = context.user_data['servicio']

    if servicio == 'drywall':
        await update.message.reply_text(
            "💡 **¿Incluimos Iluminación LED?**\n\n"
            "Escribe los **metros lineales** de luz LED que deseas instalar.\n"
            "_(Si no quieres LED, escribe 0)_"
        )
        return INGRESAR_LED
    else:
        context.user_data['led_metros'] = 0
        return await generar_presupuesto_final(update, context)

async def procesar_led(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    if not texto.isdigit():
        await update.message.reply_text("⚠️ Escribe un número (0 si no quieres LED).")
        return INGRESAR_LED
    
    context.user_data['led_metros'] = int(texto)
    return await generar_presupuesto_final(update, context)

async def generar_presupuesto_final(update: Update, context: ContextTypes.DEFAULT_TYPE):
    servicio = context.user_data['servicio']
    metros = context.user_data['metros']
    led = context.user_data.get('led_metros', 0)
    usuario = update.effective_user.first_name
    
    precio_total = 0
    detalles = []
    materiales_texto = []
    notas = "Todos los precios están sujetos a cambios."

    if servicio == 'drywall':
        # NUEVA REGLA DRYWALL
        if metros < 15:
            precio_metro = 40
            costo_base = metros * precio_metro
            detalles.append(f"Mano de obra y Materiales (Tarifa Proyectos Pequeños): {metros}m2 x ${precio_metro}")
        else:
            precio_metro = 30
            costo_base = metros * precio_metro
            detalles.append(f"Mano de obra y Materiales (Tarifa Estándar): {metros}m2 x ${precio_metro}")
            
        detalles.append(f"Subtotal Drywall: ${costo_base}")
        
        costo_led = led * 30
        if led > 0:
            detalles.append(f"Iluminación LED y Perfilería ({led}ml x $30): ${costo_led}")
        
        precio_total = costo_base + costo_led
        
        # Materiales Drywall
        laminas = ceil(metros / 2.88)
        mastique = ceil(metros / 10)
        tornillos = laminas * 36
        perfiles = ceil(metros * 1.5)
        
        materiales_texto = [
            f"- Laminas de Yeso: Aprox {laminas} u.",
            f"- Estructura Metálica: Aprox {perfiles} u.",
            f"- Tornillería estimada: {tornillos} unid.",
            f"- Mastique (Cunete): {mastique} u."
        ]

    elif servicio == 'microcemento':
        # REGLA MICROCEMENTO
        if metros <= 4:
            precio_total = 100
            detalles.append(f"Promoción Pared Decorativa (Hasta 4m2): $100 TARIFA PLANA")
        else:
            precio_total = metros * 35
            detalles.append(f"Aplicación Microcemento ({metros}m2 x $35): ${precio_total}")
        
        materiales_texto = [
            "- Kit Microcemento (Base + Fino)",
            "- Malla de fibra de vidrio",
            "- Sellador Poliuretano de alto tráfico"
        ]

    elif servicio == 'resina':
        precio_total = metros * 60
        detalles.append(f"Piso Resina Epóxica ({metros}m2 x $60): ${precio_total}")
        
        materiales_texto = [
            "- Resina Epóxica (Componente A+B)",
            "- Pigmentos Metálicos",
            "- Alcohol Isopropílico (Corrector)"
        ]

    # --- GENERAR PDF ---
    pdf = PresupuestoPDF()
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"Presupuesto Estimado: {servicio.upper()}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Cliente: {usuario}", 0, 1)
    pdf.cell(0, 10, f"Dimensiones: {metros} m2", 0, 1)
    if led > 0: pdf.cell(0, 10, f"Iluminación LED: {led} metros lineales", 0, 1)
    pdf.ln(10)
    
    pdf.set_fill_color(224, 216, 200)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "DESGLOSE DE INVERSIÓN", 1, 1, 'C', 1)
    
    pdf.set_font("Arial", "", 12)
    for linea in detalles:
        pdf.cell(0, 10, linea, 1, 1)
    
    pdf.set_font("Arial", "B", 14)
    pdf.set_text_color(10, 26, 42)
    pdf.cell(0, 15, f"TOTAL ESTIMADO: ${precio_total} USD", 1, 1, 'R')
    
    pdf.ln(10)
    
    pdf.set_text_color(0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "LISTA ESTIMADA DE MATERIALES", 0, 1)
    pdf.set_font("Arial", "", 11)
    for mat in materiales_texto:
        pdf.cell(0, 8, mat, 0, 1)
        
    pdf.ln(5)
    pdf.set_font("Arial", "I", 10)
    pdf.multi_cell(0, 5, f"Nota: {notas} Este cálculo es referencial, para una cotización final se requiere visita técnica.")

    nombre_pdf = f"Presupuesto_{servicio}_{usuario}.pdf"
    pdf.output(nombre_pdf)

    await update.message.reply_text("⏳ **Calculando...** Generando PDF oficial...")
    
    chat_id = update.effective_chat.id
    with open(nombre_pdf, 'rb') as doc:
        await context.bot.send_document(
            chat_id=chat_id,
            document=doc,
            caption=f"✅ **¡Listo {usuario}!**\n\nAquí tienes tu presupuesto preliminar.\n\n👇 **Para confirmar precio final y agendar visita:**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📲 Cerrar Trato por WhatsApp", url='https://wa.me/584123015376')]])
        )
    
    try:
        os.remove(nombre_pdf)
    except:
        pass

    await update.message.reply_text(
        "¿Deseas calcular otro proyecto?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Nuevo Cálculo", callback_data='reiniciar')]])
    )
    return ConversationHandler.END

async def reiniciar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await start(update, context)

if __name__ == '__main__':
    application = ApplicationBuilder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CallbackQueryHandler(reiniciar, pattern='^reiniciar$')],
        states={
            SELECCIONAR_SERVICIO: [CallbackQueryHandler(pedir_metros, pattern='^(drywall|microcemento|resina)$')],
            INGRESAR_METROS: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_metros)],
            INGRESAR_LED: [MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_led)]
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    print("🤖 ASENSO BOT 2.0: ACTIVO (REGLAS ACTUALIZADAS)...")

    application.run_polling()
