from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import json
import os
from datetime import datetime

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
class BorrowedBook:
    book_id: str
    fecha: str
    quantity: int = 1
    

    def to_dict(self) -> dict:
        return {
            "book_id": self.book_id,
            "quantity": self.quantity,
            "fecha":self.fecha
        }

    @staticmethod
    def from_dict(d: dict) -> "BorrowedBook":
        return BorrowedBook(
            book_id=d["book_id"],
            quantity=int(d.get("quantity", 1)),
            fecha=d["fecha"]
        )

@dataclass
class User:
    id: str
    name: str
    email: str
    borrowed: List[BorrowedBook] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "borrowed": [bb.to_dict() for bb in self.borrowed],
        }

    @staticmethod
    def from_dict(d: dict) -> "User":
        borrowed_data = d.get("borrowed", [])
        borrowed_books = []
        
        # Manejar tanto el formato antiguo como el nuevo
        for item in borrowed_data:
            if isinstance(item, str):
                # Formato antiguo: "B001" → convertir a objeto
                borrowed_books.append(BorrowedBook(book_id=item))
            else:
                # Formato nuevo: {"book_id": "B001", "quantity": 2}
                borrowed_books.append(BorrowedBook.from_dict(item))
                
        return User(
            id=d["id"],
            name=d["name"],
            email=d["email"],
            borrowed=borrowed_books,
        )

class LibraryStore:
    def __init__(self, data_file: str = "library_data.json"):
        self.data_file = data_file
        self.books: List[Book] = []
        self.users: List[User] = []
        self.undo_stack: List[Dict[str, Any]] = []
        self._load()

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

    def borrow_book(self, user_id: str, book_id: str,fecha:datetime) -> str:
        user = self.find_user(user_id)
        book = self.find_book(book_id)
        if not user: return f"[X] Usuario {user_id} no existe."
        if not book: return f"[X] Libro {book_id} no existe."
        
        if book.copies_available > 0:
            book.copies_available -= 1
            
            # BUSCAR SI EL USUARIO YA TIENE ESTE LIBRO
            found = False
            for borrowed_book in user.borrowed:
                if borrowed_book.book_id == book_id:
                    borrowed_book.quantity += 1
                    found = True
                    break
            
            # SI NO LO TIENE, AGREGARLO
            if not found:
                user.borrowed.append(BorrowedBook(book_id=book_id,fecha=fecha))
            
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
        user = self.find_user(user_id)
        book = self.find_book(book_id)
        if not user: return f"[X] Usuario {user_id} no existe."
        if not book: return f"[X] Libro {book_id} no existe."
        
        # BUSCAR EL LIBRO PRESTADO
        borrowed_item = None
        for bb in user.borrowed:
            if bb.book_id == book_id:
                borrowed_item = bb
                break
        
        if not borrowed_item:
            return f"[X] {user.name} no tiene prestado '{book.title}'."
        
        # DISMINUIR CANTIDAD O ELIMINAR
        borrowed_item.quantity -= 1
        if borrowed_item.quantity <= 0:
            user.borrowed.remove(borrowed_item)
        
        book.copies_available += 1
        autoloan_to_next = None
        
        if book.reservations:
            next_user_id = book.reservations.popleft()
            next_user = self.find_user(next_user_id)
            if next_user:
                book.copies_available -= 1
                # AGREGAR AL SIGUIENTE USUARIO (misma lógica que borrow)
                found = False
                for borrowed_book in next_user.borrowed:
                    if borrowed_book.book_id == book_id:
                        borrowed_book.quantity += 1
                        found = True
                        break
                if not found:
                    next_user.borrowed.append(BorrowedBook(book_id=book_id,fecha=datetime.now().date()))
                autoloan_to_next = next_user_id
                msg_auto = f" y asignado automáticamente a {next_user.name} por reserva."
            else:
                msg_auto = " (el siguiente en cola ya no existe)."
        else:
            msg_auto = ""
            
        self.undo_stack.append({"op": "return", "user_id": user_id, "book_id": book_id,"fecha": borrowed_item.fecha,"autoloan_to_next": autoloan_to_next})
        self._save()
        return f"[✓] Devolución de '{book.title}' registrada{msg_auto} Disponibles: {book.copies_available}."

    def undo_last(self) -> str:
        if not self.undo_stack: return "[i] No hay operaciones para deshacer."
        last = self.undo_stack.pop()
        op = last.get("op")
        
        if op == "borrow":
            user = self.find_user(last["user_id"])
            book = self.find_book(last["book_id"])
            if user and book:
                # BUSCAR Y ELIMINAR/DISMINUIR EL LIBRO PRESTADO
                for borrowed_book in user.borrowed:
                    if borrowed_book.book_id == book.id:
                        borrowed_book.quantity -= 1
                        if borrowed_book.quantity <= 0:
                            user.borrowed.remove(borrowed_book)
                        book.copies_available += 1
                        self._save()
                        return f"[↶] Deshecho: préstamo de '{book.title}' a {user.name}."
            return "[X] No se pudo deshacer el préstamo."
            
        elif op == "return":
            user = self.find_user(last["user_id"])
            book = self.find_book(last["book_id"])
            if not user or not book: return "[X] No se pudo deshacer la devolución."
            
            next_user_id = last.get("autoloan_to_next")
            if next_user_id:
                next_user = self.find_user(next_user_id)
                if next_user:
                    # ELIMINAR PRÉSTAMO AUTOMÁTICO
                    for borrowed_book in next_user.borrowed:
                        if borrowed_book.book_id == book.id:
                            borrowed_book.quantity -= 1
                            if borrowed_book.quantity <= 0:
                                next_user.borrowed.remove(borrowed_book)
                            book.reservations.appendleft(next_user_id)
                            book.copies_available += 1
                            break
            
            if book.copies_available > 0:
                book.copies_available -= 1
                # AGREGAR LIBRO AL USUARIO (misma lógica que borrow)
                found = False
                for borrowed_book in user.borrowed:
                    if borrowed_book.book_id == book.id:
                        borrowed_book.quantity += 1
                        found = True
                        break
                if not found:
                    fecha=last["fecha"]
                    user.borrowed.append(BorrowedBook(book_id=book.id,fecha=fecha))
                    
                self._save()
                return f"[↶] Deshecho: devolución de '{book.title}' de {user.name}."
            return "[X] No se pudo deshacer: no hay copia disponible."
        else:
            return "[X] Operación desconocida en pila."