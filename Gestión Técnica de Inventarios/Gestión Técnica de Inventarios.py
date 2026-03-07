
import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3

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

# --- CLASE CRUD OPTIMIZADA ---
class ModuloCRUD(tk.Frame):
    def __init__(self, parent, tabla, columnas, fields):
        super().__init__(parent, bg="white")
        self.tabla = tabla
        self.fields = fields
        self.inputs = {}
        self.combos_info = {}

        # UI: Formulario con estética de Fe y Alegría
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

        # Panel de búsqueda y ordenamiento avanzado
        search_frame = tk.Frame(self, bg="white")
        search_frame.pack(fill="x", padx=20)
        
        tk.Label(search_frame, text="🔍 Buscar:", bg="white", font=("Helvetica", 9, "bold")).pack(side="left")
        self.ent_search = tk.Entry(search_frame, font=("Helvetica", 10))
        self.ent_search.pack(side="left", fill="x", expand=True, padx=10)
        self.ent_search.bind("<KeyRelease>", lambda e: self.read(self.ent_search.get()))

        # BOTÓN: Ordenar por Especialidad / Encargado
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

        # UI: Botones CRUD
        btn_frame = tk.Frame(self, bg="white")
        btn_frame.pack(pady=10)
        
        btns = [
            ("Crear", "#cf0024", self.create),
            ("Actualizar", "#cf0024", self.update),
            ("Borrar", "#cf0024", self.delete)
        ]

        for text, color, cmd in btns:
            fg_col = "white" if text != "Actualizar" else "white"
            tk.Button(btn_frame, text=text, bg=color, fg=fg_col, width=12, 
                      font=("Helvetica", 9, "bold"), relief="flat", command=cmd).pack(side="left", padx=8)

        # UI: Tabla
        self.tree = ttk.Treeview(self, columns=columnas, show="headings")
        for col in columnas: self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)
        
        self.tree.bind("<<TreeviewSelect>>", self.cargar_seleccion)
        self.read()

    def ordenar_por_criterio(self):
        """Ordena los datos según la relación técnica (Especialidad o Encargado)"""
        for i in self.tree.get_children(): self.tree.delete(i)
        
        if self.tabla == "inventario":
            # Ordena por el nombre del Usuario asignado (Encargado)
            query = """SELECT i.id, i.item, i.cantidad, u.nombre FROM inventario i 
                       LEFT JOIN usuarios u ON i.user_id = u.id ORDER BY u.nombre ASC"""
        elif self.tabla == "usuarios":
            # Ordena por el nombre de la Especialidad
            query = """SELECT u.id, u.nombre, e.nombre FROM usuarios u 
                       LEFT JOIN especialidades e ON u.esp_id = e.id ORDER BY e.nombre ASC"""
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
            query = """SELECT i.id, i.item, i.cantidad, u.nombre FROM inventario i 
                       LEFT JOIN usuarios u ON i.user_id = u.id WHERE i.item LIKE ?"""
            data = query_db(query, ('%' + filter_text + '%',))
        elif self.tabla == "usuarios":
            data = query_db("SELECT u.id, u.nombre, e.nombre FROM usuarios u LEFT JOIN especialidades e ON u.esp_id = e.id")
        else:
            data = query_db(f"SELECT * FROM {self.tabla}")
        for fila in data: self.tree.insert("", "end", values=fila)

    def prestar_herramienta(self):
        sel = self.tree.selection()
        if not sel: return messagebox.showwarning("Atención", "Seleccione un ítem")
        item_id, _, cant_actual, _ = self.tree.item(sel)['values']
        if cant_actual <= 0: return messagebox.showerror("Error", "Sin stock.")
        try:
            user_id = self.inputs['user_id'].get().split("ID:")[1].replace(")", "")
        except: return messagebox.showwarning("Atención", "Seleccione un Responsable")
        query_db("UPDATE inventario SET cantidad = cantidad - 1 WHERE id = ?", (item_id,))
        query_db("INSERT INTO prestamos (inventario_id, usuario_id, fecha) VALUES (?, ?, datetime('now'))", (item_id, user_id))
        self.read()

    def devolver_herramienta(self):
        sel = self.tree.selection()
        if not sel: return
        item_id = self.tree.item(sel)['values'][0]
        prestamo = query_db("SELECT id FROM prestamos WHERE inventario_id = ? LIMIT 1", (item_id,))
        if not prestamo: return messagebox.showwarning("Info", "No está en uso.")
        query_db("UPDATE inventario SET cantidad = cantidad + 1 WHERE id = ?", (item_id,))
        query_db("DELETE FROM prestamos WHERE id = ?", (prestamo[0][0],))
        self.read()

    def create(self):
        try:
            vals = [self.inputs[l].get().split("ID:")[1].replace(")", "") if isinstance(self.inputs[l], ttk.Combobox) else self.inputs[l].get() for l in self.fields]
            query_db(f"INSERT INTO {self.tabla} ({','.join(self.fields.keys())}) VALUES ({','.join(['?']*len(vals))})", vals)
            self.read()
        except: messagebox.showerror("Error", "Datos incompletos")

    def delete(self):
        sel = self.tree.selection()
        if sel:
            id_reg = self.tree.item(sel)['values'][0]
            query_db(f"DELETE FROM {self.tabla} WHERE id=?", (id_reg,))
            self.read()

    def update(self):
        sel = self.tree.selection()
        if sel:
            id_reg = self.tree.item(sel)['values'][0]
            try:
                vals = [self.inputs[l].get().split("ID:")[1].replace(")", "") if isinstance(self.inputs[l], ttk.Combobox) else self.inputs[l].get() for l in self.fields]
                set_str = ", ".join([f"{k}=?" for k in self.fields.keys()])
                query_db(f"UPDATE {self.tabla} SET {set_str} WHERE id=?", vals + [id_reg])
                self.read()
            except: messagebox.showerror("Error", "Verifique los datos")

# --- APP PRINCIPAL ---
def abrir_sistema():
    main_win = tk.Toplevel()
    main_win.title("Fe y Alegría - Gestión Técnica de Inventarios")
    main_win.geometry("1100x750")
    main_win.configure(bg="#f8f9fa")
    
# --- PRIMERO DEFINES LA FUNCIÓN ---
    def cerrar_sesion():
        if messagebox.askyesno("Cerrar Sesión", "¿Está seguro de que desea salir?"):
            # 1. Limpiamos los campos del Login
            e_user.delete(0, tk.END)
            e_pass.delete(0, tk.END)
            
            # 2. Cerramos la ventana actual y mostramos el login vacío
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

   # (Aquí va el código del logo que ya tienes...)

    tk.Label(header, text="GESTIÓN TÉCNICA DE INVENTARIOS", fg="white", bg="#cf0024", 
             font=("Helvetica", 16, "bold")).pack(side="left", padx=10)
    
   # AQUÍ VA EL BOTÓN:
    tk.Button(header, text="Cerrar Sesión", bg="white", fg="#cf0024", 
              font=("Helvetica", 9, "bold"), command=cerrar_sesion, # <--- Llama a la función de arriba
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

tk.Label(root, text="Contraseña:", bg="white", font=("Helvetica", 9, "bold")).pack()
e_pass = tk.Entry(root, show="*", font=("Helvetica", 11), justify="center", bd=1, relief="solid"); e_pass.pack(pady=5)

tk.Button(root, text="ENTRAR", command=login, bg="#cf0024", fg="white", 
          font=("Helvetica", 10, "bold"), width=15, relief="flat", pady=8).pack(pady=25)

root.mainloop()
