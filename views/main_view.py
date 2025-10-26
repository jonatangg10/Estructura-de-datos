from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QMessageBox, QDesktopWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox
)
from PyQt5.QtCore import Qt

class MainView(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestión de Biblioteca — Estructuras Lineales")
        self.resize(900, 560)
        self.center()
        self.setStyleSheet("background-color: #F5F5DC;")

        tabs = QTabWidget()
        tabs.addTab(self._tab_books(), "Libros")
        tabs.addTab(self._tab_users(), "Usuarios")
        tabs.addTab(self._tab_loans(), "Préstamos")

        lay = QVBoxLayout()
        lay.addWidget(tabs)
        self.setLayout(lay)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def _tune_table(self, table: QTableWidget):
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.horizontalHeader().setHighlightSections(False)
        table.setSortingEnabled(True)

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

        self.btn_add_book = QPushButton("Registrar libro")
        self.btn_add_book.setStyleSheet(self._primary_btn_style())

        self.btn_list_books = QPushButton("Listar libros")

        self.book_filter = QLineEdit()
        self.book_filter.setPlaceholderText("Filtrar libros (ID, Título, Autor, Año, Totales, Disponibles, En cola)…")
        self.book_filter.setVisible(False)

        self.table_books = QTableWidget()
        self.table_books.setColumnCount(7)
        self.table_books.setHorizontalHeaderLabels(["ID", "Título", "Autor", "Año", "Totales", "Disponibles", "En cola"])
        self._tune_table(self.table_books)
        self.table_books.setVisible(False)

        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(self.btn_add_book)
        col.addWidget(self.btn_list_books)
        col.addWidget(self.book_filter)
        col.addWidget(self.table_books)
        w.setLayout(col)
        return w

    def _tab_users(self):
        w = QWidget()
        form = QFormLayout()
        self.user_id = QLineEdit()
        self.user_name = QLineEdit()
        self.user_email = QLineEdit()
        form.addRow("ID:", self.user_id)
        form.addRow("Nombre:", self.user_name)
        form.addRow("Email:", self.user_email)
    
        self.btn_add_user = QPushButton("Registrar usuario")
        self.btn_add_user.setStyleSheet(self._primary_btn_style())
    
        self.btn_list_users = QPushButton("Listar usuarios")
    
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Filtrar usuarios (ID, Nombre, Email o Prestados)…")
        self.user_filter.setVisible(False)
    
        # TABLA CON 5 COLUMNAS
        self.table_users = QTableWidget()
        self.table_users.setColumnCount(5)
        self.table_users.setHorizontalHeaderLabels([
            "ID", 
            "Nombre", 
            "Email", 
            "Libros Prestados", 
            "Cantidad"
        ])
        self._tune_table(self.table_users)
        self.table_users.setVisible(False)
    
        col = QVBoxLayout()
        col.addLayout(form)
        col.addWidget(self.btn_add_user)
        col.addWidget(self.btn_list_users)
        col.addWidget(self.user_filter)
        col.addWidget(self.table_users)
        w.setLayout(col)
        return w

    def _tab_loans(self):
        w = QWidget()
        form = QFormLayout()

        self.loan_user_combo = QComboBox()
        self.loan_user_combo.setEditable(True)
        self.loan_user_combo.setInsertPolicy(QComboBox.NoInsert)

        self.loan_book_combo = QComboBox()
        self.loan_book_combo.setEditable(True)
        self.loan_book_combo.setInsertPolicy(QComboBox.NoInsert)

        form.addRow("ID Usuario:", self.loan_user_combo)
        form.addRow("ID Libro:", self.loan_book_combo)

        self.btn_borrow = QPushButton("Prestar")
        self.btn_borrow.setStyleSheet(self._primary_btn_style())
        
        self.btn_return = QPushButton("Devolver")
        self.btn_undo = QPushButton("Deshacer último")

        row_btns = QHBoxLayout()
        row_btns.addWidget(self.btn_borrow)
        row_btns.addWidget(self.btn_return)
        row_btns.addWidget(self.btn_undo)

        col = QVBoxLayout()
        col.addLayout(form)
        col.addLayout(row_btns)
        w.setLayout(col)
        return w