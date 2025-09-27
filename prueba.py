from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import sys

from PyQt5.QtWidgets import (
    QApplication, QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QListWidget, QMessageBox, QDesktopWidget
)

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
    reservations: deque = field(default_factory=deque)  # cola de usuarios en espera

    def __post_init__(self):
        self.copies_available = self.copies_total


@dataclass
class User:
    id: str
    name: str
    email: str
    borrowed: List[str] = field(default_factory=list)  # ids de libros prestados


class LibraryStore:
    """
    Almacenamiento usando Estructuras de Datos Lineales:
      - libros: lista (arreglo dinámico) de Book
      - usuarios: lista (arreglo dinámico) de User
      - undo_stack: pila para deshacer la última operación (préstamo/devolución)
      - cada Book contiene una cola (deque) para reservas
    """
    def __init__(self):
        self.books: List[Book] = []
        self.users: List[User] = []
        self.undo_stack: List[Dict[str, Any]] = []  # pila de historial

    # ------ utilidades de búsqueda (búsqueda lineal) ------
    def find_book(self, book_id: str) -> Optional[Book]:
        for b in self.books:  # O(n)
            if b.id == book_id:
                return b
        return None

    def find_user(self, user_id: str) -> Optional[User]:
        for u in self.users:  # O(n)
            if u.id == user_id:
                return u
        return None

    # ------ operaciones CRUD ------
    def add_book(self, book: Book) -> str:
        if self.find_book(book.id):
            return f"[X] Ya existe un libro con ID {book.id}."
        self.books.append(book)
        return f"[✓] Libro '{book.title}' agregado."

    def add_user(self, user: User) -> str:
        if self.find_user(user.id):
            return f"[X] Ya existe un usuario con ID {user.id}."
        self.users.append(user)
        return f"[✓] Usuario '{user.name}' agregado."

    # ------ préstamo/devolución/reserva ------
    def borrow_book(self, user_id: str, book_id: str) -> str:
        user = self.find_user(user_id)
        book = self.find_book(book_id)
        if not user:
            return f"[X] Usuario {user_id} no existe."
        if not book:
            return f"[X] Libro {book_id} no existe."

        if book.copies_available > 0:
            book.copies_available -= 1
            user.borrowed.append(book.id)
            # registrar en pila para deshacer
            self.undo_stack.append({"op": "borrow", "user_id": user_id, "book_id": book_id})
            return f"[✓] Préstamo exitoso: '{book.title}' para {user.name}. Disponibles: {book.copies_available}."
        else:
            # encolar reserva
            if user_id in book.reservations:
                return f"[i] {user.name} ya está en la lista de espera de '{book.title}'."
            book.reservations.append(user_id)
            return f"[→] Sin copias. {user.name} quedó en cola de reserva para '{book.title}'. Posición: {len(book.reservations)}."

    def return_book(self, user_id: str, book_id: str) -> str:
        user = self.find_user(user_id)
        book = self.find_book(book_id)
        if not user:
            return f"[X] Usuario {user_id} no existe."
        if not book:
            return f"[X] Libro {book_id} no existe."
        if book_id not in user.borrowed:
            return f"[X] {user.name} no tiene prestado '{book.title}'."

        # quitar de prestados
        user.borrowed.remove(book_id)
        book.copies_available += 1

        autoloan_to_next = None
        # si hay reservas, entregar automáticamente al siguiente
        if book.reservations:
            next_user_id = book.reservations.popleft()
            next_user = self.find_user(next_user_id)
            if next_user:
                # consumir la copia que acabamos de liberar
                book.copies_available -= 1
                next_user.borrowed.append(book.id)
                autoloan_to_next = next_user_id
                msg_auto = f" y asignado automáticamente a {next_user.name} por reserva."
            else:
                msg_auto = " (el siguiente en cola ya no existe)."
        else:
            msg_auto = ""

        # registrar para deshacer
        self.undo_stack.append({
            "op": "return", "user_id": user_id, "book_id": book_id, "autoloan_to_next": autoloan_to_next
        })

        return f"[✓] Devolución de '{book.title}' registrada{msg_auto} Disponibles: {book.copies_available}."

    def undo_last(self) -> str:
        if not self.undo_stack:
            return "[i] No hay operaciones para deshacer."
        last = self.undo_stack.pop()
        op = last.get("op")
        if op == "borrow":
            # revertir préstamo
            user = self.find_user(last["user_id"]) 
            book = self.find_book(last["book_id"]) 
            if user and book and book.id in user.borrowed:
                user.borrowed.remove(book.id)
                book.copies_available += 1
                return f"[↶] Deshecho: préstamo de '{book.title}' a {user.name}."
            return "[X] No se pudo deshacer el préstamo."
        elif op == "return":
            user = self.find_user(last["user_id"]) 
            book = self.find_book(last["book_id"]) 
            if not user or not book:
                return "[X] No se pudo deshacer la devolución."
            # Revertimos posibles auto-asignaciones
            next_user_id = last.get("autoloan_to_next")
            if next_user_id:
                next_user = self.find_user(next_user_id)
                if next_user and book.id in next_user.borrowed:
                    next_user.borrowed.remove(book.id)
                    # reinsertar en la cola al frente por justicia de turno
                    book.reservations.appendleft(next_user_id)
                    book.copies_available += 1
            # Restaurar estado anterior: quitar copia disponible y devolver a prestados del usuario original
            if book.copies_available > 0:
                book.copies_available -= 1
                user.borrowed.append(book.id)
                return f"[↶] Deshecho: devolución de '{book.title}' de {user.name}."
            else:
                return "[X] No se pudo deshacer: no hay copia disponible para revertir."
        else:
            return "[X] Operación desconocida en pila de deshacer."

    # ------ listados para UI ------
    def list_books_text(self) -> List[str]:
        out = []
        for b in self.books:
            out.append(f"{b.id} | {b.title} | {b.author} | {b.year} | tot:{b.copies_total} disp:{b.copies_available} colaresv:{len(b.reservations)}")
        return out

    def list_users_text(self) -> List[str]:
        out = []
        for u in self.users:
            out.append(f"{u.id} | {u.name} | {u.email} | prestados:{len(u.borrowed)} -> {u.borrowed}")
        return out


# =============================
# ======== VISTA/GUI ==========
# =============================

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Biblioteca — Estructuras Lineales")
        self.resize(820, 520)
        self.center()
        self.setStyleSheet("background-color: #F5F5DC;")  # hueso

        self.store = LibraryStore()

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._tab_books(), "Libros")
        tabs.addTab(self._tab_users(), "Usuarios")
        tabs.addTab(self._tab_loans(), "Préstamos")

        lay = QVBoxLayout()
        lay.addWidget(tabs)
        self.setLayout(lay)

        # Datos de ejemplo para probar rápido
        self._seed_sample_data()

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # ---------- Pestaña Libros ----------
    def _tab_books(self):
        w = QWidget()
        form = QFormLayout()
        self.book_id = QLineEdit()
        self.book_title = QLineEdit()
        self.book_author = QLineEdit()
        self.book_year = QLineEdit()
        self.book_copies = QLineEdit()

        form.addRow("ID:", self.book_id)
        form.addRow("Título:", self.book_title)
        form.addRow("Autor:", self.book_author)
        form.addRow("Año:", self.book_year)
        form.addRow("Copias totales:", self.book_copies)

        btn_add = QPushButton("Registrar libro")
        btn_add.setStyleSheet(self._primary_btn_style())
        btn_add.clicked.connect(self.on_add_book)

        btn_list = QPushButton("Listar libros")
        btn_list.clicked.connect(self.on_list_books)

        self.list_books = QListWidget()

        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(btn_add)
        col.addWidget(btn_list)
        col.addWidget(self.list_books)

        w.setLayout(col)
        return w

    # ---------- Pestaña Usuarios ----------
    def _tab_users(self):
        w = QWidget()
        form = QFormLayout()
        self.user_id = QLineEdit()
        self.user_name = QLineEdit()
        self.user_email = QLineEdit()

        form.addRow("ID:", self.user_id)
        form.addRow("Nombre:", self.user_name)
        form.addRow("Email:", self.user_email)

        btn_add = QPushButton("Registrar usuario")
        btn_add.setStyleSheet(self._primary_btn_style())
        btn_add.clicked.connect(self.on_add_user)

        btn_list = QPushButton("Listar usuarios")
        btn_list.clicked.connect(self.on_list_users)

        self.list_users = QListWidget()

        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(btn_add)
        col.addWidget(btn_list)
        col.addWidget(self.list_users)

        w.setLayout(col)
        return w

    # ---------- Pestaña Préstamos ----------
    def _tab_loans(self):
        w = QWidget()
        form = QFormLayout()
        self.loan_user_id = QLineEdit()
        self.loan_book_id = QLineEdit()
        form.addRow("ID Usuario:", self.loan_user_id)
        form.addRow("ID Libro:", self.loan_book_id)

        row_btns = QHBoxLayout()
        btn_borrow = QPushButton("Prestar")
        btn_borrow.setStyleSheet(self._primary_btn_style())
        btn_borrow.clicked.connect(self.on_borrow)
        btn_return = QPushButton("Devolver")
        btn_return.clicked.connect(self.on_return)
        btn_undo = QPushButton("Deshacer último")
        btn_undo.clicked.connect(self.on_undo)
        row_btns.addWidget(btn_borrow)
        row_btns.addWidget(btn_return)
        row_btns.addWidget(btn_undo)

        self.log = QListWidget()

        col = QVBoxLayout()
        col.addLayout(form)
        col.addLayout(row_btns)
        col.addWidget(QLabel("Actividad:"))
        col.addWidget(self.log)

        w.setLayout(col)
        return w

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

    # ---------- Slots Libros ----------
    def on_add_book(self):
        try:
            y = int(self.book_year.text())
            c = int(self.book_copies.text())
        except ValueError:
            self._alert("Año y copias deben ser números enteros.")
            return
        msg = self.store.add_book(Book(
            id=self.book_id.text().strip(),
            title=self.book_title.text().strip(),
            author=self.book_author.text().strip(),
            year=y,
            copies_total=c
        ))
        self._log(msg)
        self.on_list_books()

    def on_list_books(self):
        self.list_books.clear()
        for line in self.store.list_books_text():
            self.list_books.addItem(line)

    # ---------- Slots Usuarios ----------
    def on_add_user(self):
        uid = self.user_id.text().strip()
        name = self.user_name.text().strip()
        email = self.user_email.text().strip()
        if not uid or not name or not email:
            self._alert("Todos los campos de usuario son obligatorios.")
            return
        msg = self.store.add_user(User(id=uid, name=name, email=email))
        self._log(msg)
        self.on_list_users()

    def on_list_users(self):
        self.list_users.clear()
        for line in self.store.list_users_text():
            self.list_users.addItem(line)

    # ---------- Slots Préstamos ----------
    def on_borrow(self):
        uid = self.loan_user_id.text().strip()
        bid = self.loan_book_id.text().strip()
        if not uid or not bid:
            self._alert("Debes indicar ID de usuario y de libro.")
            return
        msg = self.store.borrow_book(uid, bid)
        self._log(msg)
        self.on_list_books()
        self.on_list_users()

    def on_return(self):
        uid = self.loan_user_id.text().strip()
        bid = self.loan_book_id.text().strip()
        if not uid or not bid:
            self._alert("Debes indicar ID de usuario y de libro.")
            return
        msg = self.store.return_book(uid, bid)
        self._log(msg)
        self.on_list_books()
        self.on_list_users()

    def on_undo(self):
        msg = self.store.undo_last()
        self._log(msg)
        self.on_list_books()
        self.on_list_users()

    # ---------- utilidades UI ----------
    def _alert(self, text: str):
        QMessageBox.information(self, "Aviso", text)

    def _log(self, text: str):
        self.log.addItem(text)
        self.log.scrollToBottom()

    def _seed_sample_data(self):
        # libros
        self.store.add_book(Book(id="B001", title="El Quijote", author="Cervantes", year=1605, copies_total=2))
        self.store.add_book(Book(id="B002", title="Cien años de soledad", author="García Márquez", year=1967, copies_total=1))
        # usuarios
        self.store.add_user(User(id="U001", name="Ana", email="ana@example.com"))
        self.store.add_user(User(id="U002", name="Luis", email="luis@example.com"))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
