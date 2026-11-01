"""Command-line interface. Run with: python -m task_manager.cli"""

from __future__ import annotations

from .core import Task, TaskError, TaskManager, ValidationError

MENU = """
1. Add task
2. List tasks
3. Complete task
4. Delete task
5. Quit"""


def format_task(task: Task) -> str:
    mark = "x" if task.done else " "
    return f"[{mark}] {task.id}. {task.title}"


def print_tasks(manager: TaskManager) -> None:
    tasks = manager.list_tasks()
    if not tasks:
        print("\nNo tasks yet.")
        return
    print("\n=== Your tasks ===")
    for task in tasks:
        print(format_task(task))


def ask_task_id(prompt: str) -> int:
    raw = input(prompt).strip()
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(f"'{raw}' is not a valid task ID.") from None


def add_task(manager: TaskManager) -> None:
    task = manager.add_task(input("Task title: "))
    print(f"\nTask '{task.title}' added.")


def complete_task(manager: TaskManager) -> None:
    print_tasks(manager)
    task = manager.complete_task(ask_task_id("\nID of the task to complete: "))
    print(f"\nTask '{task.title}' marked as done.")


def delete_task(manager: TaskManager) -> None:
    print_tasks(manager)
    task_id = ask_task_id("\nID of the task to delete: ")
    manager.delete_task(task_id)
    print(f"\nTask {task_id} deleted.")


ACTIONS = {
    "1": add_task,
    "2": print_tasks,
    "3": complete_task,
    "4": delete_task,
}


def run(manager: TaskManager) -> None:
    if manager.recovered_from:
        print(
            "Warning: the database file was corrupted and has been moved to "
            f"{manager.recovered_from}. Starting with an empty task list."
        )
    print("=== Task Manager ===")

    while True:
        print(MENU)
        choice = input("\nChoose an option: ").strip()
        if choice == "5":
            print("Bye!")
            return
        action = ACTIONS.get(choice)
        if action is None:
            print("Invalid option.")
            continue
        try:
            action(manager)
        except TaskError as error:
            print(f"\nError: {error}")


def main() -> None:
    try:
        run(TaskManager())
    except (KeyboardInterrupt, EOFError):
        print("\nBye!")


if __name__ == "__main__":
    main()
