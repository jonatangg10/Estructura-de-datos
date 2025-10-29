from datetime import datetime
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
from PyQt5.QtCore import Qt

from models.library_models import LibraryStore, Book, User
from views.main_view import MainView

class LibraryController:
    def __init__(self):
        self.view = MainView()
        self.model = LibraryStore()
        self.model.seed_if_empty()
        
        self._connect_signals()
        self._refresh_loan_combos()

    def _connect_signals(self):
        # Libros
        self.view.btn_add_book.clicked.connect(self.on_add_book)
        self.view.btn_list_books.clicked.connect(self.on_toggle_list_books)
        self.view.book_filter.textChanged.connect(self.filter_books_table)
        
        # Usuarios
        self.view.btn_add_user.clicked.connect(self.on_add_user)
        self.view.btn_list_users.clicked.connect(self.on_toggle_list_users)
        self.view.user_filter.textChanged.connect(self.filter_users_table)
        
        # Préstamos
        self.view.btn_borrow.clicked.connect(self.on_borrow)
        self.view.btn_return.clicked.connect(self.on_return)
        self.view.btn_undo.clicked.connect(self.on_undo)
        #listado de prestado
        self.view.btn_list_prestados.clicked.connect(self.on_toggle_list_prestados)
        self.view.prestados_filter.textChanged.connect(self.filter_prestamos_table)
        # reservas
        self.view.btn_list_reservas.clicked.connect(self.on_toggle_list_reservas)
        self.view.reservas_filter.textChanged.connect(self.filter_reservas_table)

    def _refresh_loan_combos(self):
        # Usuarios (sin cambios)
        current_user = self.view.loan_user_combo.currentText()
        self.view.loan_user_combo.blockSignals(True)
        self.view.loan_user_combo.clear()
        for u in self.model.users:
            self.view.loan_user_combo.addItem(f"{u.name} ({u.id})", userData=u.id)
        if current_user and current_user not in [self.view.loan_user_combo.itemText(i) for i in range(self.view.loan_user_combo.count())]:
            self.view.loan_user_combo.setEditText(current_user)
        self.view.loan_user_combo.blockSignals(False)
    
        # Libros: MOSTRAR TODOS, no solo los disponibles
        current_book = self.view.loan_book_combo.currentText()
        self.view.loan_book_combo.blockSignals(True)
        self.view.loan_book_combo.clear()
        
        for b in self.model.books:
            # Mostrar información de disponibilidad
            if b.copies_available > 0:
                display_text = f"{b.id} — {b.title} (Disponible: {b.copies_available})"
            else:
                # Mostrar información de la cola de espera
                queue_position = len(b.reservations)
                display_text = f"{b.id} — {b.title} (En cola: {queue_position})"
            
            self.view.loan_book_combo.addItem(display_text, userData=b.id)
        
        if current_book and current_book not in [self.view.loan_book_combo.itemText(i) for i in range(self.view.loan_book_combo.count())]:
            self.view.loan_book_combo.setEditText(current_book)
        self.view.loan_book_combo.blockSignals(False)

    def _notify(self, text: str, level: str = "info", timeout_ms: int = 10000):
        mb = QMessageBox(self.view)
        mb.setWindowTitle("Aviso")

        # Personalizar mensajes según el tipo
        if "→" in text:  # Mensaje de cola de espera
            mb.setIcon(QMessageBox.Information)
            mb.setText(f"📋 {text}")
        elif "✓" in text:  # Mensaje de éxito
            mb.setIcon(QMessageBox.Information) 
            mb.setText(f"✅ {text}")
        elif "X" in text:  # Mensaje de error
            mb.setIcon(QMessageBox.Critical)
            mb.setText(f"❌ {text}")
        elif "↶" in text:  # Mensaje de deshacer
            mb.setIcon(QMessageBox.Information)
            mb.setText(f"↩️ {text}")
        else:  # Mensaje informativo
            mb.setIcon(QMessageBox.Information)
            mb.setText(f"ℹ️ {text}")

        mb.setStandardButtons(QMessageBox.Ok)
        mb.setWindowModality(Qt.NonModal)
        mb.show()
        QTimer.singleShot(timeout_ms, mb.close)
        self._write_log(text)

    def _write_log(self, text: str, path: str = "library_actions.log"):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {text}\n")
        except Exception as e:
            mb = QMessageBox(self.view)
            mb.setWindowTitle("Aviso")
            mb.setIcon(QMessageBox.Warning)
            mb.setText(f"[LOG] No se pudo escribir en {path}: {e}")
            mb.setStandardButtons(QMessageBox.Ok)
            mb.setWindowModality(Qt.NonModal)
            mb.show()
            QTimer.singleShot(4000, mb.close)

    # Libros
    def on_add_book(self):
        try:
            y = int(self.view.book_year.text())
            c = int(self.view.book_copies.text())
        except ValueError:
            self._notify("Año y copias deben ser números enteros.", "error", 7000)
            return
        
        msg = self.model.add_book(Book(
            id=self.view.book_id.text().strip(),
            title=self.view.book_title.text().strip(),
            author=self.view.book_author.text().strip(),
            year=y, copies_total=c
        ))
        self._notify(msg)
        
        if self.view.table_books.isVisible():
            self.on_list_books()
        self._refresh_loan_combos()

    def on_toggle_list_books(self):
        if not self.view.table_books.isVisible():
            self.on_list_books()
            self.view.table_books.setVisible(True)
            self.view.book_filter.setVisible(True)
            self.view.book_filter.setFocus()
            self.view.btn_list_books.setText("Ocultar lista de libros")
        else:
            self.view.table_books.setVisible(False)
            self.view.book_filter.clear()
            self.view.book_filter.setVisible(False)
            self.view.btn_list_books.setText("Listar libros")

    def on_list_books(self):
        books = self.model.books
        self.view.table_books.setRowCount(len(books))
        for row, b in enumerate(books):
            # Resaltar libros con cola de espera
            en_cola = len(b.reservations)
            if en_cola > 0:
                disponibles_text = f"{b.copies_available} ⚠️({en_cola} en cola)"
            else:
                disponibles_text = str(b.copies_available)
                
            data = [b.id, b.title, b.author, str(b.year),
                    str(b.copies_total), disponibles_text,
                    str(en_cola)]
            for col, val in enumerate(data):
                self.view.table_books.setItem(row, col, QTableWidgetItem(val))
        
        if self.view.book_filter.isVisible() and self.view.book_filter.text().strip():
            self.filter_books_table(self.view.book_filter.text())

    def filter_books_table(self, text: str):
        text = text.strip().lower()
        rows = self.view.table_books.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.view.table_books.columnCount()):
                    item = self.view.table_books.item(r, c)
                    if item and text in item.text().lower():
                        show = True
                        break
            self.view.table_books.setRowHidden(r, not show)

    # Usuarios
    def on_add_user(self):
        uid = self.view.user_id.text().strip()
        name = self.view.user_name.text().strip()
        email = self.view.user_email.text().strip()
        
        if not uid or not name or not email:
            self._notify("Todos los campos de usuario son obligatorios.", "warn", 8000)
            return
        
        msg = self.model.add_user(User(id=uid, name=name, email=email))
        self._notify(msg)

        # LIMPIAR LOS INPUTS DESPUÉS DE REGISTRAR
        self.view.user_id.clear()
        self.view.user_name.clear()
        self.view.user_email.clear()
        
        if self.view.table_users.isVisible():
            self.on_list_users()
        self._refresh_loan_combos()

    def on_toggle_list_users(self):
        if not self.view.table_users.isVisible():
            self.on_list_users()
            self.view.table_users.setVisible(True)
            self.view.user_filter.setVisible(True)
            self.view.user_filter.setFocus()
            self.view.btn_list_users.setText("Ocultar lista de usuarios")
        else:
            self.view.table_users.setVisible(False)
            self.view.user_filter.clear()
            self.view.user_filter.setVisible(False)
            self.view.btn_list_users.setText("Listar usuarios")

    def on_list_users(self):
        users = self.model.users
        self.view.table_users.setRowCount(len(users))

        for row, u in enumerate(users):
            self.view.table_users.setItem(row, 0, QTableWidgetItem(u.id))
            self.view.table_users.setItem(row, 1, QTableWidgetItem(u.name))
            self.view.table_users.setItem(row, 2, QTableWidgetItem(u.email))

            # PROCESAR LIBROS PRESTADOS CON EL NUEVO FORMATO
            libros_info = []
            total_libros = 0

            for borrowed_book in u.borrowed:
                book = self.model.find_book(borrowed_book.book_id)
                if book:
                    if borrowed_book.quantity > 1:
                        libros_info.append(f"{book.title} (x{borrowed_book.quantity})")
                    else:
                        libros_info.append(book.title)
                    total_libros += borrowed_book.quantity
                else:
                    if borrowed_book.quantity > 1:
                        libros_info.append(f"Libro no encontrado {borrowed_book.book_id} (x{borrowed_book.quantity})")
                    else:
                        libros_info.append(f"Libro no encontrado {borrowed_book.book_id}")
                    total_libros += borrowed_book.quantity

            prestados_text = ", ".join(libros_info) if libros_info else "Ninguno"
            cantidad_text = str(total_libros)

            self.view.table_users.setItem(row, 3, QTableWidgetItem(prestados_text))
            self.view.table_users.setItem(row, 4, QTableWidgetItem(cantidad_text))

        # Aplicar filtro si está activo
        if self.view.user_filter.isVisible() and self.view.user_filter.text().strip():
            self.filter_users_table(self.view.user_filter.text())

    def filter_users_table(self, text: str):
        text = text.strip().lower()
        rows = self.view.table_users.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.view.table_users.columnCount()):
                    item = self.view.table_users.item(r, c)
                    if item and text in item.text().lower():
                        show = True
                        break
            self.view.table_users.setRowHidden(r, not show)

    # Préstamos
    def on_borrow(self):
        # Obtener IDs
        user_id = self.view.loan_user_combo.currentData()
        if not user_id:
            user_text = self.view.loan_user_combo.currentText().strip()
            user_id = self._extract_user_id(user_text)

        book_id = self.view.loan_book_combo.currentData()
        if not book_id:
            book_text = self.view.loan_book_combo.currentText().strip()
            book_id = self._extract_book_id(book_text)

        if not user_id or not book_id:
            self._notify("Debes indicar ID de usuario y de libro.", "warn", 8000)
            return
        
        fecha=self.view.prestamo_fecha.dateTime().toPyDateTime().date()
        if fecha < datetime.now().date():
            self._notify("No puedes indicar una fecha menor a la actual.", "warn", 8000)
            return

        msg = self.model.borrow_book(user_id, book_id,fecha.isoformat())
        self._notify(msg)

        # Actualizar las vistas
        if self.view.table_books.isVisible():
            self.on_list_books()
        if self.view.table_users.isVisible():
            self.on_list_users()
        self._refresh_loan_combos()  # Esto actualizará la información de disponibilidad

    def on_return(self):
        # Obtener el texto seleccionado del combo
        user_text = self.view.loan_user_combo.currentText().strip()

        # Extraer solo el ID del usuario
        user_id = self._extract_user_id(user_text)

        # Obtener el ID del libro
        book_id = self.view.loan_book_combo.currentData()
        if not book_id:
            book_text = self.view.loan_book_combo.currentText().strip()
            book_id = self._extract_book_id(book_text)

        if not user_id or not book_id:
            self._notify("Debes indicar ID de usuario y de libro.", "warn", 8000)
            return

        msg = self.model.return_book(user_id, book_id)  # <-- Usar user_id extraído
        self._notify(msg)

        if self.view.table_books.isVisible():
            self.on_list_books()
        if self.view.table_users.isVisible():
            self.on_list_users()
        self._refresh_loan_combos()

    def _extract_user_id(self, user_text: str) -> str:
        """Extrae el ID de usuario del texto del ComboBox"""
        if not user_text:
            return ""

        # Buscar texto entre paréntesis: "Ana (U001)" → "U001"
        import re
        match = re.search(r'\(([^)]+)\)', user_text)
        if match:
            return match.group(1)  # Devuelve lo que está entre paréntesis

        # Si no hay paréntesis, asumir que es solo el ID
        return user_text

    def _extract_book_id(self, book_text: str) -> str:
        """Extrae el ID del libro del texto del ComboBox"""
        if not book_text:
            return ""

        # Buscar el ID al inicio: "B001 — El Quijote" → "B001"
        parts = book_text.split('—')
        if parts:
            return parts[0].strip()  # Devuelve la primera parte antes del "—"

        return book_text.strip()

    def on_undo(self):
        msg = self.model.undo_last()
        self._notify(msg)
        
        if self.view.table_books.isVisible():
            self.on_list_books()
        if self.view.table_users.isVisible():
            self.on_list_users()
        self._refresh_loan_combos()



    # funciones listado de prestados

    def on_toggle_list_prestados(self):
        if not self.view.table_prestamos.isVisible():
            self.on_list_prestados()
            self.view.table_prestamos.setVisible(True)
            self.view.prestados_filter.setVisible(True)
            self.view.prestados_filter.setFocus()
            self.view.btn_list_prestados.setText("Ocultar lista de Prestamos")
        else:
            self.view.table_prestamos.setVisible(False)
            self.view.prestados_filter.clear()
            self.view.prestados_filter.setVisible(False)
            self.view.btn_list_prestados.setText("Listar Prestamos")

    def on_list_prestados(self):
        users = self.model.users
        self.view.table_prestamos.setRowCount(sum(len(u.borrowed) for u in users if u.borrowed))
        row=0
        for u in users:
            for borrowed_book in u.borrowed:
                book = self.model.find_book(borrowed_book.book_id)         
                self.view.table_prestamos.setItem(row, 0, QTableWidgetItem(f"{borrowed_book.book_id} - {self.model.find_book(borrowed_book.book_id).title}"))
                self.view.table_prestamos.setItem(row, 1, QTableWidgetItem(f"{u.id} - {u.name}"))
                self.view.table_prestamos.setItem(row, 2, QTableWidgetItem(f"{borrowed_book.quantity}"))
                self.view.table_prestamos.setItem(row, 3, QTableWidgetItem(f"{borrowed_book.fecha}"))
                row+=1
        # Aplicar filtro si está activo
        if self.view.prestados_filter.isVisible() and self.view.prestados_filter.text().strip():
            self.filter_prestamos_table(self.view.prestados_filter.text())

    def filter_prestamos_table(self, text: str):
        text = text.strip().lower()
        rows = self.view.table_prestamos.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.view.table_prestamos.columnCount()):
                    item = self.view.table_prestamos.item(r, c)
                    if item and text in item.text().lower():
                        show = True
                        break
            self.view.table_prestamos.setRowHidden(r, not show)

    def on_toggle_list_reservas(self):
        if not self.view.table_reservas.isVisible():
            self.on_list_reservas()
            self.view.table_reservas.setVisible(True)
            self.view.reservas_filter.setVisible(True)
            self.view.reservas_filter.setFocus()
            self.view.btn_list_reservas.setText("Ocultar lista de Reservaciones")
        else:
            self.view.table_reservas.setVisible(False)
            self.view.reservas_filter.clear()
            self.view.reservas_filter.setVisible(False)
            self.view.btn_list_reservas.setText("Listar Reservaciones")

    def on_list_reservas(self):
        book = self.model.books
        self.view.table_reservas.setRowCount(sum(len(u.reservations) for u in book if u.reservations))
        row=0
        for u in book:
            for reserva_book in u.reservations:         
                self.view.table_reservas.setItem(row, 0, QTableWidgetItem(f"{u.id} - {u.title}"))
                self.view.table_reservas.setItem(row, 1, QTableWidgetItem(f"{reserva_book} - {self.model.find_user(reserva_book).name}"))
                row+=1
        # Aplicar filtro si está activo
        if self.view.reservas_filter.isVisible() and self.view.reservas_filter.text().strip():
            self.filter_reservas_table(self.view.reservas_filter.text())

    def filter_reservas_table(self, text: str):
        text = text.strip().lower()
        rows = self.view.table_reservas.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.view.table_reservas.columnCount()):
                    item = self.view.table_reservas.item(r, c)
                    if item and text in item.text().lower():
                        show = True
                        break
            self.view.table_reservas.setRowHidden(r, not show)

    def show(self):
        self.view.show()