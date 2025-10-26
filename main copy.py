from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import sys
import json, os
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QDesktopWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox   # <-- QComboBox
)
from PyQt5.QtCore import QTimer, Qt

# =============================
# ======== MODELO =============
# =============================

@dataclass
class Book:
    id: str
    title: str
    author: str
    year: int
    copies_total: int
    copies_available: int = field(init=False)
    reservations: deque = field(default_factory=deque)

    def __post_init__(self):
        if not hasattr(self, "copies_available") or self.copies_available is None:
            self.copies_available = self.copies_total

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "year": self.year,
            "copies_total": self.copies_total,
            "copies_available": self.copies_available,
            "reservations": list(self.reservations),
        }

    @staticmethod
    def from_dict(d: dict) -> "Book":
        b = Book(
            id=d["id"],
            title=d["title"],
            author=d["author"],
            year=int(d["year"]),
            copies_total=int(d["copies_total"]),
        )
        b.copies_available = int(d.get("copies_available", b.copies_total))
        b.reservations = deque(d.get("reservations", []))
        return b


@dataclass
class User:
    id: str
    name: str
    email: str
    borrowed: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "borrowed": list(self.borrowed),
        }

    @staticmethod
    def from_dict(d: dict) -> "User":
        return User(
            id=d["id"],
            name=d["name"],
            email=d["email"],
            borrowed=list(d.get("borrowed", [])),
        )


class LibraryStore:
    def __init__(self, data_file: str = "library_data.json"):
        self.data_file = data_file
        self.books: List[Book] = []
        self.users: List[User] = []
        self.undo_stack: List[Dict[str, Any]] = []
        self._load()

    # --------- persistencia ----------
    def _save(self):
        data = {
            "books": [b.to_dict() for b in self.books],
            "users": [u.to_dict() for u in self.users],
        }
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self):
        if not os.path.exists(self.data_file):
            return
        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.books = [Book.from_dict(b) for b in data.get("books", [])]
            self.users = [User.from_dict(u) for u in data.get("users", [])]
        except Exception as e:
            print(f"[WARN] No se pudo cargar {self.data_file}: {e}")

    def seed_if_empty(self):
        if not self.books and not self.users:
            self.add_book(Book(id="B001", title="El Quijote", author="Cervantes", year=1605, copies_total=2))
            self.add_book(Book(id="B002", title="Cien años de soledad", author="García Márquez", year=1967, copies_total=1))
            self.add_user(User(id="U001", name="Ana", email="ana@example.com"))
            self.add_user(User(id="U002", name="Luis", email="luis@example.com"))

    # --------- búsqueda ----------
    def find_book(self, book_id: str) -> Optional[Book]:
        for b in self.books:
            if b.id == book_id:
                return b
        return None

    def find_user(self, user_id: str) -> Optional[User]:
        for u in self.users:
            if u.id == user_id:
                return u
        return None

    # --------- comandos ----------
    def add_book(self, book: Book) -> str:
        if self.find_book(book.id):
            return f"[X] Ya existe un libro con ID {book.id}."
        self.books.append(book)
        self._save()
        return f"[✓] Libro '{book.title}' agregado."

    def add_user(self, user: User) -> str:
        if self.find_user(user.id):
            return f"[X] Ya existe un usuario con ID {user.id}."
        self.users.append(user)
        self._save()
        return f"[✓] Usuario '{user.name}' agregado."

    def borrow_book(self, user_id: str, book_id: str) -> str:
        user = self.find_user(user_id); book = self.find_book(book_id)
        if not user: return f"[X] Usuario {user_id} no existe."
        if not book: return f"[X] Libro {book_id} no existe."
        if book.copies_available > 0:
            book.copies_available -= 1
            user.borrowed.append(book.id)
            self.undo_stack.append({"op": "borrow", "user_id": user_id, "book_id": book_id})
            self._save()
            return f"[✓] Préstamo exitoso: '{book.title}' para {user.name}. Disponibles: {book.copies_available}."
        else:
            if user_id in book.reservations:
                return f"[i] {user.name} ya está en la lista de espera de '{book.title}'."
            book.reservations.append(user_id)
            self._save()
            return f"[→] Sin copias. {user.name} quedó en cola para '{book.title}'. Posición: {len(book.reservations)}."

    def return_book(self, user_id: str, book_id: str) -> str:
        user = self.find_user(user_id); book = self.find_book(book_id)
        if not user: return f"[X] Usuario {user_id} no existe."
        if not book: return f"[X] Libro {book_id} no existe."
        if book_id not in user.borrowed: return f"[X] {user.name} no tiene prestado '{book.title}'."
        user.borrowed.remove(book_id); book.copies_available += 1
        autoloan_to_next = None
        if book.reservations:
            next_user_id = book.reservations.popleft()
            next_user = self.find_user(next_user_id)
            if next_user:
                book.copies_available -= 1
                next_user.borrowed.append(book.id)
                autoloan_to_next = next_user_id
                msg_auto = f" y asignado automáticamente a {next_user.name} por reserva."
            else:
                msg_auto = " (el siguiente en cola ya no existe)."
        else:
            msg_auto = ""
        self.undo_stack.append({"op": "return", "user_id": user_id, "book_id": book_id, "autoloan_to_next": autoloan_to_next})
        self._save()
        return f"[✓] Devolución de '{book.title}' registrada{msg_auto} Disponibles: {book.copies_available}."

    def undo_last(self) -> str:
        if not self.undo_stack: return "[i] No hay operaciones para deshacer."
        last = self.undo_stack.pop(); op = last.get("op")
        if op == "borrow":
            user = self.find_user(last["user_id"]); book = self.find_book(last["book_id"])
            if user and book and book.id in user.borrowed:
                user.borrowed.remove(book.id); book.copies_available += 1
                self._save()
                return f"[↶] Deshecho: préstamo de '{book.title}' a {user.name}."
            return "[X] No se pudo deshacer el préstamo."
        elif op == "return":
            user = self.find_user(last["user_id"]); book = self.find_book(last["book_id"])
            if not user or not book: return "[X] No se pudo deshacer la devolución."
            next_user_id = last.get("autoloan_to_next")
            if next_user_id:
                next_user = self.find_user(next_user_id)
                if next_user and book.id in next_user.borrowed:
                    next_user.borrowed.remove(book.id)
                    book.reservations.appendleft(next_user_id)
                    book.copies_available += 1
            if book.copies_available > 0:
                book.copies_available -= 1; user.borrowed.append(book.id)
                self._save()
                return f"[↶] Deshecho: devolución de '{book.title}' de {user.name}."
            return "[X] No se pudo deshacer: no hay copia disponible."
        else:
            return "[X] Operación desconocida en pila."


# =============================
# ======== VISTA/GUI ==========
# =============================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Biblioteca — Estructuras Lineales")
        self.resize(900, 560)
        self.center()
        self.setStyleSheet("background-color: #F5F5DC;")

        self.store = LibraryStore()
        self.store.seed_if_empty()

        tabs = QTabWidget()
        tabs.addTab(self._tab_books(), "Libros")
        tabs.addTab(self._tab_users(), "Usuarios")
        tabs.addTab(self._tab_loans(), "Préstamos")

        lay = QVBoxLayout()
        lay.addWidget(tabs)
        self.setLayout(lay)

        # Llenar combos al iniciar
        self._refresh_loan_combos()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # ---------- Utilidad de tablas ----------
    def _tune_table(self, table: QTableWidget):
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setHighlightSections(False)
        table.setSortingEnabled(True)

    # ---------- Notificación (modal auto-cierre) ----------
    def _notify(self, text: str, level: str = "info", timeout_ms: int = 10000):
        mb = QMessageBox(self)
        mb.setWindowTitle("Aviso")
        mb.setText(text)
        if level == "error":
            mb.setIcon(QMessageBox.Critical)
        elif level == "warn":
            mb.setIcon(QMessageBox.Warning)
        else:
            mb.setIcon(QMessageBox.Information)
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
            mb = QMessageBox(self)
            mb.setWindowTitle("Aviso")
            mb.setIcon(QMessageBox.Warning)
            mb.setText(f"[LOG] No se pudo escribir en {path}: {e}")
            mb.setStandardButtons(QMessageBox.Ok)
            mb.setWindowModality(Qt.NonModal)
            mb.show()
            QTimer.singleShot(4000, mb.close)

    # ---------- Pestaña Libros ----------
    def _tab_books(self):
        w = QWidget()
        form = QFormLayout()
        self.book_id = QLineEdit();  self.book_title = QLineEdit()
        self.book_author = QLineEdit(); self.book_year = QLineEdit()
        self.book_copies = QLineEdit()
        form.addRow("ID:", self.book_id)
        form.addRow("Título:", self.book_title)
        form.addRow("Autor:", self.book_author)
        form.addRow("Año:", self.book_year)
        form.addRow("Copias totales:", self.book_copies)

        btn_add = QPushButton("Registrar libro")
        btn_add.setStyleSheet(self._primary_btn_style())
        btn_add.clicked.connect(self.on_add_book)

        self.btn_list_books = QPushButton("Listar libros")
        self.btn_list_books.clicked.connect(self.on_toggle_list_books)

        self.book_filter = QLineEdit()
        self.book_filter.setPlaceholderText("Filtrar libros (ID, Título, Autor, Año, Totales, Disponibles, En cola)…")
        self.book_filter.textChanged.connect(self.filter_books_table)
        self.book_filter.setVisible(False)

        self.table_books = QTableWidget()
        self.table_books.setColumnCount(7)
        self.table_books.setHorizontalHeaderLabels(["ID", "Título", "Autor", "Año", "Totales", "Disponibles", "En cola"])
        self._tune_table(self.table_books)
        self.table_books.setVisible(False)

        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(btn_add)
        col.addWidget(self.btn_list_books)
        col.addWidget(self.book_filter)
        col.addWidget(self.table_books)
        w.setLayout(col)
        return w

    # ---------- Pestaña Usuarios ----------
    def _tab_users(self):
        w = QWidget()
        form = QFormLayout()
        self.user_id = QLineEdit(); self.user_name = QLineEdit(); self.user_email = QLineEdit()
        form.addRow("ID:", self.user_id); form.addRow("Nombre:", self.user_name); form.addRow("Email:", self.user_email)

        btn_add = QPushButton("Registrar usuario")
        btn_add.setStyleSheet(self._primary_btn_style())
        btn_add.clicked.connect(self.on_add_user)

        self.btn_list_users = QPushButton("Listar usuarios")
        self.btn_list_users.clicked.connect(self.on_toggle_list_users)

        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Filtrar usuarios (ID, Nombre, Email o Prestados)…")
        self.user_filter.textChanged.connect(self.filter_users_table)
        self.user_filter.setVisible(False)

        self.table_users = QTableWidget()
        self.table_users.setColumnCount(4)
        self.table_users.setHorizontalHeaderLabels(["ID", "Nombre", "Email", "Prestados"])
        self._tune_table(self.table_users)
        self.table_users.setVisible(False)

        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(btn_add)
        col.addWidget(self.btn_list_users)
        col.addWidget(self.user_filter)
        col.addWidget(self.table_users)
        w.setLayout(col)
        return w

    # ---------- Pestaña Préstamos ----------
    def _tab_loans(self):
        w = QWidget()
        form = QFormLayout()

        # Combos (desplegables) en vez de QLineEdit
        self.loan_user_combo = QComboBox()
        self.loan_user_combo.setEditable(True)
        self.loan_user_combo.setInsertPolicy(QComboBox.NoInsert)

        self.loan_book_combo = QComboBox()
        self.loan_book_combo.setEditable(True)
        self.loan_book_combo.setInsertPolicy(QComboBox.NoInsert)

        form.addRow("ID Usuario:", self.loan_user_combo)
        form.addRow("ID Libro:", self.loan_book_combo)

        row_btns = QHBoxLayout()
        btn_borrow = QPushButton("Prestar"); btn_borrow.setStyleSheet(self._primary_btn_style()); btn_borrow.clicked.connect(self.on_borrow)
        btn_return = QPushButton("Devolver"); btn_return.clicked.connect(self.on_return)
        btn_undo = QPushButton("Deshacer último"); btn_undo.clicked.connect(self.on_undo)
        row_btns.addWidget(btn_borrow); row_btns.addWidget(btn_return); row_btns.addWidget(btn_undo)

        col = QVBoxLayout()
        col.addLayout(form); col.addLayout(row_btns)
        w.setLayout(col); return w

    # ---------- Estilos ----------
    def _primary_btn_style(self) -> str:
        return (
            "QPushButton {"
            "background-color: #32CD32;"
            "color: white;"
            "font-size: 15px;"
            "font-weight: bold;"
            "border-radius: 8px;"
            "padding: 8px 12px;"
            "}"
            "QPushButton:hover {"
            "background-color: #228B22;"
            "}"
        )

    # ---------- Helpers de combos ----------
    def _refresh_loan_combos(self):
        # Usuarios: todos
        if hasattr(self, "loan_user_combo"):
            current_user = self.loan_user_combo.currentText()
            self.loan_user_combo.blockSignals(True)
            self.loan_user_combo.clear()
            for u in self.store.users:
                # Si quieres mostrar nombre: f"{u.id} — {u.name}"
                # self.loan_user_combo.addItem(u.id)
                self.loan_user_combo.addItem(f"{u.name} ({u.id})", userData=u.id)
            if current_user and current_user not in [self.loan_user_combo.itemText(i) for i in range(self.loan_user_combo.count())]:
                self.loan_user_combo.setEditText(current_user)
            self.loan_user_combo.blockSignals(False)

        # Libros: solo disponibles
        if hasattr(self, "loan_book_combo"):
            current_book = self.loan_book_combo.currentText()
            self.loan_book_combo.blockSignals(True)
            self.loan_book_combo.clear()
            for b in self.store.books:
                if b.copies_available > 0:
                    # Mostrar título también (opcional):
                    self.loan_book_combo.addItem(f"{b.id} — {b.title}", userData=b.id)
            # restaurar texto si no coincide con alguna opción
            if current_book and current_book not in [self.loan_book_combo.itemText(i) for i in range(self.loan_book_combo.count())]:
                self.loan_book_combo.setEditText(current_book)
            self.loan_book_combo.blockSignals(False)

    # ---------- Libros ----------
    def on_add_book(self):
        try:
            y = int(self.book_year.text()); c = int(self.book_copies.text())
        except ValueError:
            self._notify("Año y copias deben ser números enteros.", "error", 7000); return
        msg = self.store.add_book(Book(
            id=self.book_id.text().strip(),
            title=self.book_title.text().strip(),
            author=self.book_author.text().strip(),
            year=y, copies_total=c
        ))
        self._notify(msg)
        if self.table_books.isVisible(): self.on_list_books()
        self._refresh_loan_combos()  # actualizar combos

    def on_toggle_list_books(self):
        if not self.table_books.isVisible():
            self.on_list_books()
            self.table_books.setVisible(True)
            self.book_filter.setVisible(True)
            self.book_filter.setFocus()
            self.btn_list_books.setText("Ocultar lista de libros")
        else:
            self.table_books.setVisible(False)
            self.book_filter.clear()
            self.book_filter.setVisible(False)
            self.btn_list_books.setText("Listar libros")

    def on_list_books(self):
        books = self.store.books
        self.table_books.setRowCount(len(books))
        for row, b in enumerate(books):
            data = [b.id, b.title, b.author, str(b.year),
                    str(b.copies_total), str(b.copies_available),
                    str(len(b.reservations))]
            for col, val in enumerate(data):
                self.table_books.setItem(row, col, QTableWidgetItem(val))
        if self.book_filter.isVisible() and self.book_filter.text().strip():
            self.filter_books_table(self.book_filter.text())

    def filter_books_table(self, text: str):
        text = text.strip().lower()
        rows = self.table_books.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.table_books.columnCount()):
                    item = self.table_books.item(r, c)
                    if item and text in item.text().lower():
                        show = True; break
            self.table_books.setRowHidden(r, not show)

    # ---------- Usuarios ----------
    def on_add_user(self):
        uid = self.user_id.text().strip(); name = self.user_name.text().strip(); email = self.user_email.text().strip()
        if not uid or not name or not email:
            self._notify("Todos los campos de usuario son obligatorios.", "warn", 8000); return
        msg = self.store.add_user(User(id=uid, name=name, email=email))
        self._notify(msg)
        if self.table_users.isVisible(): self.on_list_users()
        self._refresh_loan_combos()  # actualizar combos

    def on_toggle_list_users(self):
        if not self.table_users.isVisible():
            self.on_list_users()
            self.table_users.setVisible(True)
            self.user_filter.setVisible(True)
            self.user_filter.setFocus()
            self.btn_list_users.setText("Ocultar lista de usuarios")
        else:
            self.table_users.setVisible(False)
            self.user_filter.clear()
            self.user_filter.setVisible(False)
            self.btn_list_users.setText("Listar usuarios")

    def on_list_users(self):
        users = self.store.users
        self.table_users.setRowCount(len(users))
        for row, u in enumerate(users):
            self.table_users.setItem(row, 0, QTableWidgetItem(u.id))
            self.table_users.setItem(row, 1, QTableWidgetItem(u.name))
            self.table_users.setItem(row, 2, QTableWidgetItem(u.email))
            prestados = ", ".join(u.borrowed) if u.borrowed else "—"
            self.table_users.setItem(row, 3, QTableWidgetItem(prestados))
        if self.user_filter.isVisible() and self.user_filter.text().strip():
            self.filter_users_table(self.user_filter.text())

    def filter_users_table(self, text: str):
        text = text.strip().lower()
        rows = self.table_users.rowCount()
        for r in range(rows):
            show = not bool(text)
            if text:
                for c in range(self.table_users.columnCount()):
                    item = self.table_users.item(r, c)
                    if item and text in item.text().lower():
                        show = True; break
            self.table_users.setRowHidden(r, not show)

    # ---------- Préstamos ----------
    def on_borrow(self):
        # obtener ID del usuario
        uid = self.loan_user_combo.currentText().strip() if hasattr(self, "loan_user_combo") else ""
        # obtener ID del libro (si usamos userData guardamos el id puro)
        if hasattr(self, "loan_book_combo"):
            bid = self.loan_book_combo.currentData()
            if not bid:
                bid = self.loan_book_combo.currentText().strip()
        else:
            bid = ""
        if not uid or not bid:
            self._notify("Debes indicar ID de usuario y de libro.", "warn", 8000); return

        msg = self.store.borrow_book(uid, bid)
        self._notify(msg)

        if hasattr(self, "table_books") and self.table_books.isVisible(): self.on_list_books()
        if hasattr(self, "table_users") and self.table_users.isVisible(): self.on_list_users()
        self._refresh_loan_combos()  # actualizar opciones tras prestar

    def on_return(self):
        uid = self.loan_user_combo.currentText().strip() if hasattr(self, "loan_user_combo") else ""
        if hasattr(self, "loan_book_combo"):
            bid = self.loan_book_combo.currentData()
            if not bid:
                bid = self.loan_book_combo.currentText().strip()
        else:
            bid = ""
        if not uid or not bid:
            self._notify("Debes indicar ID de usuario y de libro.", "warn", 8000); return

        msg = self.store.return_book(uid, bid)
        self._notify(msg)

        if hasattr(self, "table_books") and self.table_books.isVisible(): self.on_list_books()
        if hasattr(self, "table_users") and self.table_users.isVisible(): self.on_list_users()
        self._refresh_loan_combos()  # actualizar opciones tras devolver

    def on_undo(self):
        msg = self.store.undo_last()
        self._notify(msg)
        if hasattr(self, "table_books") and self.table_books.isVisible(): self.on_list_books()
        if hasattr(self, "table_users") and self.table_users.isVisible(): self.on_list_users()
        self._refresh_loan_combos()  # actualizar opciones tras deshacer


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
