import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime
import os
import subprocess # Necesario para abrir la carpeta de forma segura
import os
import sys
import sys

def resource_path(relative_path):
    """ Gestiona rutas para archivos internos en el .exe """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Y cuando llames a la imagen en tu código, usa:
# logo_ruta = resource_path("logo.png")
# img_login = tk.PhotoImage(file=logo_ruta)

# --- NUEVAS IMPORTACIONES PARA PDF ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

# --- GESTIÓN DE BASE DE DATOS ---
def query_db(query, parameters=()):
    with sqlite3.connect("sistema_tecnico.db") as conn:
        cursor = conn.cursor()
        cursor.execute(query, parameters)
        conn.commit()
        return cursor.fetchall()

def inicializar_db():
    query_db("CREATE TABLE IF NOT EXISTS especialidades (id INTEGER PRIMARY KEY, nombre TEXT)")
    query_db("CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY, nombre TEXT, esp_id INTEGER, FOREIGN KEY(esp_id) REFERENCES especialidades(id))")
    query_db("CREATE TABLE IF NOT EXISTS inventario (id INTEGER PRIMARY KEY, item TEXT, cantidad INTEGER, user_id INTEGER, FOREIGN KEY(user_id) REFERENCES usuarios(id))")
    
    query_db("""CREATE TABLE IF NOT EXISTS prestamos (
                id INTEGER PRIMARY KEY, 
                inventario_id INTEGER, 
                usuario_id INTEGER, 
                fecha TEXT,
                FOREIGN KEY(inventario_id) REFERENCES inventario(id),
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id))""")

    if not query_db("SELECT * FROM especialidades"):
        for esp in ['Telemática', 'Electricidad', 'Electrónica', 'Metalmecánica']:
            query_db("INSERT INTO especialidades (nombre) VALUES (?)", (esp,))

# --- CLASE CRUD OPTIMIZADA CON EXPORTACIÓN PDF ---
class ModuloCRUD(tk.Frame):
    def __init__(self, parent, tabla, columnas, fields):
        super().__init__(parent, bg="white")
        self.tabla = tabla
        self.fields = fields
        self.inputs = {}
        self.combos_info = {}

        # UI: Formulario
        frame_top = tk.LabelFrame(self, text=f" Gestión de {tabla.capitalize()} ", 
                                  font=("Helvetica", 10, "bold"), bg="white", fg="#cf0024", padx=10, pady=10)
        frame_top.pack(fill="x", padx=20, pady=15)

        for i, (label, tipo) in enumerate(fields.items()):
            tk.Label(frame_top, text=label.capitalize()+":", bg="white", font=("Helvetica", 9)).grid(row=0, column=i*2, padx=5, pady=5)
            if tipo == "text" or tipo == "int":
                res = tk.Entry(frame_top, highlightthickness=1, highlightbackground="#ccc")
            else: 
                res = ttk.Combobox(frame_top, state="readonly")
                self.combos_info[label] = tipo
            res.grid(row=0, column=i*2+1, padx=5, pady=5)
            self.inputs[label] = res

        # Panel de búsqueda
        search_frame = tk.Frame(self, bg="white")
        search_frame.pack(fill="x", padx=20)
        
        tk.Label(search_frame, text="🔍 Buscar:", bg="white", font=("Helvetica", 9, "bold")).pack(side="left")
        self.ent_search = tk.Entry(search_frame, font=("Helvetica", 10))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=10)
        self.ent_search.bind("<KeyRelease>", lambda e: self.read(self.ent_search.get()))

        texto_boton = "📂 Agrupar por Especialidad" if tabla == "usuarios" else "👤 Ordenar por Encargado"
        if tabla != "especialidades":
            tk.Button(search_frame, text=texto_boton, bg="#6c757d", fg="white", 
                      font=("Helvetica", 8, "bold"), command=self.ordenar_por_criterio, relief="flat").pack(side="right")

        if tabla == "inventario":
            loan_frame = tk.Frame(self, bg="white")
            loan_frame.pack(pady=10)
            tk.Button(loan_frame, text="🚀 Retirar para Uso", bg="#cf0024", fg="white", font=("Helvetica", 9, "bold"), 
                      relief="flat", padx=15, command=self.prestar_herramienta).pack(side="left", padx=10)
            tk.Button(loan_frame, text="📦 Devolver a Stock", bg="#cf0024", fg="white", font=("Helvetica", 9, "bold"), 
                      relief="flat", padx=15, command=self.devolver_herramienta).pack(side="left", padx=10)
            # BOTÓN NUEVO: EXPORTAR PDF
            tk.Button(loan_frame, text="📄 Generar PDF", bg="#cf0024", fg="white", font=("Helvetica", 9, "bold"), 
                      relief="flat", padx=15, command=self.exportar_pdf).pack(side="left", padx=10)

        # UI: Botones CRUD
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(pady=10)
        
        btns = [("Crear", "#cf0024", self.create), ("Actualizar", "#cf0024", self.update), ("Borrar", "#cf0024", self.delete)]

        for text, color, cmd in btns:
            tk.Button(btn_frame, text=text, bg=color, fg="white", width=12, 
                      font=("Helvetica", 9, "bold"), relief="flat", command=cmd).pack(side="left", padx=8)

        # UI: Tabla
        self.tree = ttk.Treeview(self, columns=columnas, show="headings")
        for col in columnas: self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)
        
        self.tree.bind("<<TreeviewSelect>>", self.cargar_seleccion)
        self.read()

    # --- MÉTODO PARA EXPORTAR PDF ---
    def exportar_pdf(self):
        filename = f"Reporte_{self.tabla}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        # Obtener la ruta absoluta de la carpeta donde se guardará
        ruta_carpeta = os.path.abspath(os.getcwd())
        ruta_completa = os.path.join(ruta_carpeta, filename)

        try:
            doc = SimpleDocTemplate(ruta_completa, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()
            
            # --- SECCIÓN 1: TÍTULO ---
            title = Paragraph(f"FE Y ALEGRÍA - REPORTE TÉCNICO", styles['Title'])
            elements.append(title)
            sub_title = Paragraph(f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
            elements.append(sub_title)
            elements.append(Spacer(1, 20))

            # --- SECCIÓN 2: TABLA DE INVENTARIO GENERAL ---
            elements.append(Paragraph("<b>1. ESTADO ACTUAL DEL INVENTARIO</b>", styles['Heading2']))
            elements.append(Spacer(1, 10))
            
            headers_inv = [self.tree.heading(col)['text'] for col in self.tree['columns']]
            data_inv = [headers_inv]
            for child in self.tree.get_children():
                data_inv.append(self.tree.item(child)['values'])

            t_inv = Table(data_inv, hAlign='CENTER', colWidths=[40, 180, 80, 150])
            estilo_tabla = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.red),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ])
            t_inv.setStyle(estilo_tabla)
            elements.append(t_inv)
            elements.append(Spacer(1, 25))

            # --- SECCIÓN 3: HERRAMIENTAS EN USO ---
            elements.append(Paragraph("<b>2. DETALLE DE HERRAMIENTAS EN USO</b>", styles['Heading2']))
            elements.append(Spacer(1, 10))

            query_uso = """
                SELECT i.item, u.nombre, p.fecha 
                FROM prestamos p
                JOIN inventario i ON p.inventario_id = i.id
                JOIN usuarios u ON p.usuario_id = u.id
                ORDER BY p.fecha DESC
            """
            prestamos_activos = query_db(query_uso)

            if prestamos_activos:
                headers_uso = ["Herramienta", "Responsable", "Fecha Retiro"]
                data_uso = [headers_uso]
                for p in prestamos_activos: data_uso.append(list(p))

                t_uso = Table(data_uso, hAlign='CENTER', colWidths=[150, 150, 150])
                t_uso.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ]))
                elements.append(t_uso)
            else:
                elements.append(Paragraph("<i>No hay herramientas en uso actualmente.</i>", styles['Normal']))

            # --- SECCIÓN 4: FIRMA DE RESPONSABILIDAD ---
            elements.append(Spacer(1, 50))
            data_firma = [["__________________________", "__________________________"],
                          ["Firma Responsable Técnico", "Sello de la Institución"]]
            t_firma = Table(data_firma, colWidths=[225, 225])
            t_firma.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold')]))
            elements.append(t_firma)

            # Generar el archivo
            doc.build(elements)

            # --- NUEVA FUNCIÓN: AVISAR Y ABRIR CARPETA ---
            if messagebox.askyesno("Éxito", f"Reporte generado: {filename}\n\n¿Desea abrir la carpeta contenedora?"):
                # Comando para abrir el explorador de archivos en la carpeta actual (Windows)
                os.startfile(ruta_carpeta)
            
        except Exception as e:
            messagebox.showerror("Error PDF", f"Error al generar reporte: {e}")

    def ordenar_por_criterio(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.tabla == "inventario":
            query = "SELECT i.id, i.item, i.cantidad, u.nombre FROM inventario i LEFT JOIN usuarios u ON i.user_id = u.id ORDER BY u.nombre ASC"
        elif self.tabla == "usuarios":
            query = "SELECT u.id, u.nombre, e.nombre FROM usuarios u LEFT JOIN especialidades e ON u.esp_id = e.id ORDER BY e.nombre ASC"
        else:
            query = f"SELECT * FROM {self.tabla} ORDER BY id ASC"
        data = query_db(query)
        for fila in data: self.tree.insert("", "end", values=fila)

    def cargar_seleccion(self, event):
        sel = self.tree.selection()
        if not sel: return
        valores = self.tree.item(sel)['values']
        for i, (label, widget) in enumerate(self.inputs.items()):
            val_tabla = str(valores[i+1])
            if isinstance(widget, ttk.Combobox):
                for index, item in enumerate(widget['values']):
                    if val_tabla in item:
                        widget.current(index)
                        break
            else:
                widget.delete(0, tk.END)
                widget.insert(0, val_tabla)

    def update_combos(self):
        for label, tabla_ref in self.combos_info.items():
            datos = query_db(f"SELECT id, nombre FROM {tabla_ref}")
            self.inputs[label]['values'] = [f"{d[1]} (ID:{d[0]})" for d in datos]

    def read(self, filter_text=""):
        if not filter_text: self.update_combos()
        for i in self.tree.get_children(): self.tree.delete(i)
        if self.tabla == "inventario":
            query = "SELECT i.id, i.item, i.cantidad, u.nombre FROM inventario i LEFT JOIN usuarios u ON i.user_id = u.id WHERE i.item LIKE ?"
            data = query_db(query, ('%' + filter_text + '%',))
        elif self.tabla == "usuarios":
            query = "SELECT u.id, u.nombre, e.nombre FROM usuarios u LEFT JOIN especialidades e ON u.esp_id = e.id WHERE u.nombre LIKE ?"
            data = query_db(query, ('%' + filter_text + '%',))
        else:
            query = f"SELECT * FROM {self.tabla} WHERE nombre LIKE ?"
            data = query_db(query, ('%' + filter_text + '%',))
        for fila in data: self.tree.insert("", "end", values=fila)

    def prestar_herramienta(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Atención", "Seleccione un ítem")
        
        # Guardamos el ID para re-seleccionar después
        item_id, nombre_item, cant_actual, _ = self.tree.item(sel)['values']
        
        if cant_actual <= 0: return messagebox.showerror("Error", "Sin stock disponible.")
        
        try:
            user_id = self.inputs['user_id'].get().split("ID:")[1].split(")")[0].strip()
        except: 
            return messagebox.showwarning("Atención", "Seleccione un Responsable en el menú desplegable")

        # Preguntar cantidad
        opcion = messagebox.askyesnocancel("Retirar", f"¿Desea retirar TODO el stock ({cant_actual})?\n\n'Sí' para Todo / 'No' para Solo 1")
        
        if opcion is True: # Seleccionó "SÍ" (Todo)
            cantidad_a_retirar = cant_actual
        elif opcion is False: # Seleccionó "NO" (Solo 1)
            cantidad_a_retirar = 1
        else: return # Cancelar

        # Ejecutar transacción
        query_db("UPDATE inventario SET cantidad = cantidad - ? WHERE id = ?", (cantidad_a_retirar, item_id))
        for _ in range(cantidad_a_retirar):
            query_db("INSERT INTO prestamos (inventario_id, usuario_id, fecha) VALUES (?, ?, datetime('now'))", (item_id, user_id))
        
        self.read()
        self._mantener_seleccion(item_id)

    def devolver_herramienta(self):
        sel = self.tree.selection()
        if not sel: return
        
        item_id = self.tree.item(sel)['values'][0]
        
        # Contar cuántos ítems de este tipo están prestados
        prestamos_activos = query_db("SELECT id FROM prestamos WHERE inventario_id = ?", (item_id,))
        if not prestamos_activos: 
            return messagebox.showwarning("Info", "Esta herramienta no tiene unidades en uso.")

        cant_en_uso = len(prestamos_activos)
        opcion = messagebox.askyesnocancel("Devolver", f"Hay {cant_en_uso} unidades en uso.\n\n¿Desea devolver TODAS?\n'Sí' para Todas / 'No' para Solo 1")

        if opcion is True:
            cantidad_a_devolver = cant_en_uso
        elif opcion is False:
            cantidad_a_devolver = 1
        else: return

        # Ejecutar devolución
        query_db("UPDATE inventario SET cantidad = cantidad + ? WHERE id = ?", (cantidad_a_devolver, item_id))
        
        # Eliminar los registros de préstamo (los más antiguos primero)
        ids_a_borrar = [p[0] for p in prestamos_activos[:cantidad_a_devolver]]
        for id_p in ids_a_borrar:
            query_db("DELETE FROM prestamos WHERE id = ?", (id_p,))
            
        self.read()
        self._mantener_seleccion(item_id)

    def _mantener_seleccion(self, id_objetivo):
        """Función auxiliar para buscar el ID en la tabla y resaltarlo"""
        for item in self.tree.get_children():
            if self.tree.item(item)['values'][0] == id_objetivo:
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item) # Asegura que sea visible si hay scroll
                break
            
    def create(self):
        try:
            vals = []
            for l in self.fields:
                widget = self.inputs[l]
                val = widget.get()
                
                # Extraer ID numérico si es un Combobox
                if isinstance(widget, ttk.Combobox):
                    if "ID:" in val:
                        val = val.split("ID:")[1].split(")")[0].strip()
                    else:
                        return messagebox.showwarning("Atención", f"Seleccione un valor válido de la lista en {l}")
                
                if val == "":
                    return messagebox.showwarning("Atención", f"El campo {l} no puede estar vacío")
                vals.append(val)

            # Insertar usando las llaves del diccionario fields (nombres reales de columnas)
            columnas = ", ".join(self.fields.keys())
            placeholders = ", ".join(["?"] * len(vals))
            query_db(f"INSERT INTO {self.tabla} ({columnas}) VALUES ({placeholders})", vals)
            
            self.read()
            # Limpiar campos
            for w in self.inputs.values():
                if isinstance(w, ttk.Combobox): w.set('')
                else: w.delete(0, tk.END)
                
        except Exception as e: 
            messagebox.showerror("Error", f"No se pudo crear el registro: {e}")

    def delete(self):
        sel = self.tree.selection()
        if sel:
            id_reg = self.tree.item(sel)['values'][0]
            query_db(f"DELETE FROM {self.tabla} WHERE id=?", (id_reg,))
            self.read()

    def update(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Atención", "Seleccione un registro para actualizar")
        
        id_reg = self.tree.item(sel)['values'][0]
        try:
            vals = []
            for l in self.fields:
                widget = self.inputs[l]
                val = widget.get()
                
                if isinstance(widget, ttk.Combobox):
                    if "ID:" in val:
                        val = val.split("ID:")[1].split(")")[0].strip()
                    else:
                        # Si no hay ID:, es que no se cambió el valor. 
                        # Lo buscamos en la columna correspondiente del Treeview
                        val_actual = self.tree.item(sel)['values']
                        # Esta parte es técnica: buscamos el ID original si el usuario no tocó el combo
                        return messagebox.showwarning("Atención", f"Por favor, vuelva a seleccionar la opción en {l}")
                
                vals.append(val)

            set_str = ", ".join([f"{k}=?" for k in self.fields.keys()])
            query_db(f"UPDATE {self.tabla} SET {set_str} WHERE id=?", vals + [id_reg])
            self.read()
            messagebox.showinfo("Éxito", "Registro actualizado")
        except Exception as e: 
            messagebox.showerror("Error", f"Verifique los datos: {e}")

# --- APP PRINCIPAL ---
def formatear_base_datos():
    # Primera advertencia
    confirmar = messagebox.askyesno("ADVERTENCIA CRÍTICA", 
        "¿Está seguro de que desea FORMATEAR el sistema?\n\nEsto eliminará permanentemente todos los inventarios, usuarios y registros.")
    
    if confirmar:
        # Segunda advertencia
        reconfirmar = messagebox.askquestion("CONFIRMACIÓN FINAL", 
            "Esta acción NO se puede deshacer. ¿Eliminar archivo 'sistema_tecnico.db' ahora?")
        
        if reconfirmar == 'yes':
            try:
                # Forzamos una recolección de basura para cerrar cualquier puntero suelto a la DB
                import gc
                gc.collect() 

                if os.path.exists("sistema_tecnico.db"):
                    # Intentamos renombrarlo antes de borrar (truco para verificar acceso)
                    # o borrar directamente
                    os.remove("sistema_tecnico.db")
                
                messagebox.showinfo("Reinicio", "Base de datos eliminada. El programa se cerrará para aplicar los cambios.")
                
                # Usamos sys.exit() en lugar de os._exit() para un cierre más controlado
                root.destroy()
                sys.exit()
                
            except PermissionError:
                messagebox.showerror("Error de Acceso", 
                    "No se pudo eliminar la base de datos porque está en uso.\n"
                    "Cierra el programa manualmente y elimina el archivo 'sistema_tecnico.db' de la carpeta.")
            except Exception as e:
                messagebox.showerror("Error", f"Ocurrió un error inesperado: {e}")

def abrir_sistema():
    main_win = tk.Toplevel()
    main_win.title("Fe y Alegría - Gestión Técnica de Inventarios")
    main_win.geometry("1100x750")
    main_win.configure(bg="#f8f9fa")
    
    def cerrar_sesion():
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea salir?"):
            e_user.delete(0, tk.END)
            e_pass.delete(0, tk.END)
            main_win.destroy()
            root.deiconify()
    
    header = tk.Frame(main_win, bg="#cf0024", height=80)
    header.pack(fill="x")
    
    try:
        main_win.logo_img = tk.PhotoImage(file="logo.png").subsample(5, 5)
        lbl_img = tk.Label(header, image=main_win.logo_img, bg="#cf0024")
        lbl_img.pack(side="left", padx=20, pady=5)
    except:
        tk.Label(header, text="F&A", fg="white", bg="#cf0024", font=("Arial", 20, "bold")).pack(side="left", padx=20)

    tk.Label(header, text="GESTIÓN TÉCNICA DE INVENTARIOS", fg="white", bg="#cf0024", 
             font=("Helvetica", 16, "bold")).pack(side="left", padx=10)
    
    # NUEVO BOTÓN DE FORMATEO (Añadir junto al botón de Cerrar Sesión)
    tk.Button(header, text="⚠ Formatear Sistema", bg="#ffc107", fg="black", 
              font=("Helvetica", 9, "bold"), command=formatear_base_datos, 
              relief="flat", padx=10).pack(side="right", padx=10)
    
    tk.Button(header, text="Cerrar Sesión", bg="white", fg="#cf0024", 
              font=("Helvetica", 9, "bold"), command=cerrar_sesion, 
              relief="flat", padx=10).pack(side="right", padx=20)

    tabs = ttk.Notebook(main_win)
    tab_esp = ModuloCRUD(tabs, "especialidades", ("ID", "Especialidad"), {"nombre": "text"})
    tab_users = ModuloCRUD(tabs, "usuarios", ("ID", "Nombre", "Especialidad"), {"nombre": "text", "esp_id": "especialidades"})
    tab_inv = ModuloCRUD(tabs, "inventario", ("ID", "Herramienta", "Stock", "Responsable"), {"item": "text", "cantidad": "int", "user_id": "usuarios"})

    tabs.add(tab_esp, text=" ESPECIALIDADES ")
    tabs.add(tab_users, text=" PERSONAL ")
    tabs.add(tab_inv, text=" INVENTARIO ")
    tabs.pack(expand=1, fill="both", padx=10, pady=10)
    tabs.bind("<<NotebookTabChanged>>", lambda e: tabs.nametowidget(tabs.select()).read())

def login():
    if e_user.get() == "admin" and e_pass.get() == "1234":
        root.withdraw()
        abrir_sistema()
    else: messagebox.showerror("Error", "Credenciales incorrectas")

# --- PANTALLA DE LOGIN ---
inicializar_db()
root = tk.Tk()
root.title("Acceso")
root.geometry("350x500") 
root.configure(bg="white")

try:
    img_login = tk.PhotoImage(file="logo.png").subsample(3, 3)
    tk.Label(root, image=img_login, bg="white").pack(pady=20)
except:
    tk.Label(root, text="❤", fg="#cf0024", bg="white", font=("Arial", 50)).pack(pady=20)

tk.Label(root, text="FE Y ALEGRÍA", font=("Helvetica", 16, "bold"), fg="#cf0024", bg="white").pack()
tk.Label(root, text="Gestión Técnica de Inventarios", font=("Helvetica", 9), fg="gray", bg="white").pack(pady=(0,20))

tk.Label(root, text="Usuario:", bg="white", font=("Helvetica", 9, "bold")).pack()
e_user = tk.Entry(root, font=("Helvetica", 11), justify="center", bd=1, relief="solid"); e_user.pack(pady=5)
e_user.bind("<Return>", lambda e: login())

tk.Label(root, text="Contraseña:", bg="white", font=("Helvetica", 9, "bold")).pack()
e_pass = tk.Entry(root, show="*", font=("Helvetica", 11), justify="center", bd=1, relief="solid"); e_pass.pack(pady=5)
e_pass.bind("<Return>", lambda e: login())

tk.Button(root, text="ENTRAR", command=login, bg="#cf0024", fg="white", 
          font=("Helvetica", 10, "bold"), width=15, relief="flat", pady=8).pack(pady=25)


root.mainloop()






