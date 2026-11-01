import re

from playwright.sync_api import Page, expect

DONE = re.compile(r"\bis-done\b")


def task_row(page: Page, title: str):
    return page.locator(".task", has=page.locator(".task-title", has_text=title))


def add_task(page: Page, title: str, priority: str = "medium") -> None:
    page.fill("#title", title)
    page.select_option("#priority", priority)
    page.click("#add-form button[type=submit]")


def test_first_visit_loads_sample_tasks(demo):
    expect(demo.locator(".task")).to_have_count(6)
    expect(demo.locator("#progress-label")).to_have_text("2 of 6 tasks done")


def test_add_task(demo):
    add_task(demo, "Ship the demo", "high")

    expect(demo.locator(".alert-success")).to_have_text('Task "Ship the demo" added.')
    expect(task_row(demo, "Ship the demo").locator(".badge")).to_have_text("high")
    expect(demo.locator(".task")).to_have_count(7)


def test_add_blank_title_shows_error(demo):
    add_task(demo, "   ")

    expect(demo.locator("#add-error")).to_have_text("Title cannot be empty.")
    expect(demo.locator(".task")).to_have_count(6)


def test_toggle_done_and_back_to_pending(demo):
    row = task_row(demo, "Plan next sprint")

    row.locator(".check").click()
    expect(row).to_have_class(DONE)
    expect(demo.locator("#progress-label")).to_have_text("3 of 6 tasks done")

    row.locator(".check").click()
    expect(row).not_to_have_class(DONE)
    expect(demo.locator("#progress-label")).to_have_text("2 of 6 tasks done")


def test_edit_task(demo):
    task_row(demo, "Plan next sprint").get_by_role("button", name="Edit").click()
    demo.fill("#edit-title", "Plan the next two sprints")
    demo.select_option("#edit-priority", "low")
    demo.click("#edit-form button[type=submit]")

    expect(demo.locator(".alert-success")).to_have_text("Task updated.")
    row = task_row(demo, "Plan the next two sprints")
    expect(row.locator(".badge")).to_have_text("low")


def test_filter_by_status_with_counters(demo):
    expect(demo.locator("a[data-status=pending] .count")).to_have_text("4")
    expect(demo.locator("a[data-status=done] .count")).to_have_text("2")

    demo.click("a[data-status=done]")
    expect(demo.locator(".task")).to_have_count(2)
    expect(demo.locator(".task:not(.is-done)")).to_have_count(0)

    demo.click("a[data-status=pending]")
    expect(demo.locator(".task")).to_have_count(4)
    expect(demo.locator(".task.is-done")).to_have_count(0)


def test_delete_asks_for_confirmation(demo):
    row = task_row(demo, "Review pull requests")
    delete = row.get_by_role("button", name="Delete")

    demo.once("dialog", lambda dialog: dialog.dismiss())
    delete.click()
    expect(row).to_have_count(1)

    demo.once("dialog", lambda dialog: dialog.accept())
    delete.click()
    expect(row).to_have_count(0)
    expect(demo.locator(".alert-success")).to_have_text('Task "Review pull requests" deleted.')


def test_changes_persist_after_reload(demo):
    add_task(demo, "Survives a reload")
    task_row(demo, "Plan next sprint").locator(".check").click()

    demo.reload()

    expect(task_row(demo, "Survives a reload")).to_have_count(1)
    expect(task_row(demo, "Plan next sprint")).to_have_class(DONE)
    expect(demo.locator("#progress-label")).to_have_text("3 of 7 tasks done")
