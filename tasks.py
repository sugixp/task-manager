import sqlite3

# ==================== BANCO DE DADOS ====================


def conectar():
    conn = sqlite3.connect("tasks.db")
    return conn


def criar_tabela():
    conn = conectar()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            concluida INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# ==================== CRUD ====================


def criar_tarefa(titulo):
    conn = conectar()
    conn.execute("INSERT INTO tasks (titulo) VALUES (?)", (titulo,))
    conn.commit()
    conn.close()
    print(f"\nTarefa '{titulo}' adicionada com sucesso.")


def listar_tarefas():
    conn = conectar()
    cursor = conn.execute("SELECT id, titulo, concluida FROM tasks")
    tarefas = cursor.fetchall()
    conn.close()

    if not tarefas:
        print("\nNenhuma tarefa encontrada.")
        return

    print("\n=== Suas Tarefas ===")
    for tarefa in tarefas:
        status = "✓" if tarefa[2] == 1 else "✗"
        print(f"[{status}] {tarefa[0]}. {tarefa[1]}")


def concluir_tarefa(id):
    conn = conectar()
    conn.execute("UPDATE tasks SET concluida = 1 WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    print(f"\nTarefa {id} marcada como concluída.")


def deletar_tarefa(id):
    conn = conectar()
    conn.execute("DELETE FROM tasks WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    print(f"\nTarefa {id} deletada.")

# ==================== MENU ====================


def menu():
    criar_tabela()
    print("=== Gerenciador de Tarefas ===")

    while True:
        print("\n1. Adicionar tarefa")
        print("2. Listar tarefas")
        print("3. Concluir tarefa")
        print("4. Deletar tarefa")
        print("5. Sair")

        opcao = input("\nEscolha uma opção: ")

        if opcao == "1":
            titulo = input("Nome da tarefa: ")
            criar_tarefa(titulo)

        elif opcao == "2":
            listar_tarefas()

        elif opcao == "3":
            listar_tarefas()
            id = int(input("\nID da tarefa a concluir: "))
            concluir_tarefa(id)

        elif opcao == "4":
            listar_tarefas()
            id = int(input("\nID da tarefa a deletar: "))
            deletar_tarefa(id)

        elif opcao == "5":
            break

        else:
            print("Opção inválida.")


menu()
