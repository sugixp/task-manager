"""Command-line interface. Run with: python -m task_manager.cli"""

from __future__ import annotations

from .core import (
    DEFAULT_PRIORITY,
    PRIORITIES,
    STATUS_FILTERS,
    Task,
    TaskError,
    TaskManager,
    ValidationError,
)

MENU = """
1. Add task
2. List tasks
3. Edit task
4. Toggle done / pending
5. Delete task
6. Quit"""

PRIORITY_CHOICES = "/".join(PRIORITIES)
STATUS_CHOICES = "/".join(STATUS_FILTERS)


def format_task(task: Task) -> str:
    mark = "x" if task.done else " "
    return f"[{mark}] {task.id}. {task.title} ({task.priority})"


def print_tasks(manager: TaskManager, status: str = "all") -> None:
    tasks = manager.list_tasks(status)
    if not tasks:
        print("\nNo tasks here yet.")
        return
    print(f"\n=== Your tasks ({status}) ===")
    for task in tasks:
        print(format_task(task))


def ask_task_id(prompt: str) -> int:
    raw = input(prompt).strip()
    try:
        return int(raw)
    except ValueError:
        raise ValidationError(f"'{raw}' is not a valid task ID.") from None


def add_task(manager: TaskManager) -> None:
    title = input("Task title: ")
    priority = input(f"Priority ({PRIORITY_CHOICES}) [{DEFAULT_PRIORITY}]: ").strip()
    task = manager.add_task(title, priority or DEFAULT_PRIORITY)
    print(f"\nTask '{task.title}' added.")


def list_tasks(manager: TaskManager) -> None:
    status = input(f"Show ({STATUS_CHOICES}) [all]: ").strip().lower()
    print_tasks(manager, status or "all")


def edit_task(manager: TaskManager) -> None:
    print_tasks(manager)
    task = manager.get_task(ask_task_id("\nID of the task to edit: "))
    print("Leave a field blank to keep its current value.")
    title = input(f"New title [{task.title}]: ").strip()
    priority = input(f"New priority ({PRIORITY_CHOICES}) [{task.priority}]: ").strip()
    task = manager.update_task(task.id, title or None, priority or None)
    print(f"\nTask {task.id} updated: {format_task(task)}")


def toggle_task(manager: TaskManager) -> None:
    print_tasks(manager)
    task = manager.toggle_done(ask_task_id("\nID of the task to toggle: "))
    state = "done" if task.done else "pending"
    print(f"\nTask '{task.title}' marked as {state}.")


def delete_task(manager: TaskManager) -> None:
    print_tasks(manager)
    task = manager.get_task(ask_task_id("\nID of the task to delete: "))
    answer = input(f"Delete '{task.title}'? (y/N): ").strip().lower()
    if answer != "y":
        print("\nDeletion cancelled.")
        return
    manager.delete_task(task.id)
    print(f"\nTask '{task.title}' deleted.")


ACTIONS = {
    "1": add_task,
    "2": list_tasks,
    "3": edit_task,
    "4": toggle_task,
    "5": delete_task,
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
        if choice == "6":
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
