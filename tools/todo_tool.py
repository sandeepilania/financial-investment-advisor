"""A simple Todo list tool."""

from collections.abc import Callable, Sequence
from typing import Literal, Optional, TypeVar, final

from typing_extensions import override

from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from pydantic import BaseModel

from core.loggers import log_tool_call
from core.state import State

T = TypeVar("T")


def find_if(pred: Callable[[T], bool], iterable: Sequence[T]) -> T | None:
    """Find the first item in the iterable that matches the predicate.

    :param pred: A function that takes an item and returns True or False.
    :param iterable: A sequence of items to search through.
    :return: The first item that matches the predicate, or None if no match is found.
    """
    for item in filter(pred, iterable):
        return item
    return None


class Todo(BaseModel):
    """A single Todo item."""

    task: str
    state: Literal["todo", "in_progress", "done"]

    @override
    def __str__(self) -> str:
        """Return a string representation of the Todo list."""
        GREEN = "\033[32m"
        RESET = "\033[0m"
        ORANGE = "\033[38;5;208m"

        EMPTY_CHECKBOX = chr(0x2610)
        FILLED_CHECKBOX = chr(0x2611)

        match self.state:
            case "todo":
                checkbox = EMPTY_CHECKBOX
                color = RESET
            case "in_progress":
                checkbox = FILLED_CHECKBOX
                color = ORANGE
            case "done":
                checkbox = FILLED_CHECKBOX
                color = GREEN

        return f"{color}{checkbox} {self.task} {RESET}"


class TodoList(BaseModel):
    """A list of Todo items."""

    todos: list[Todo]
    session_id: Optional[str] = None  # noqa: UP045  # type: ignore[reportDeprecated]

    def __len__(self) -> int:
        """Return the number of Todo items in the list."""
        return len(self.todos)

    def __getitem__(self, index: int | slice) -> Todo | list[Todo]:
        """Get a Todo item by index."""
        return self.todos[index]

    @override
    def __str__(self) -> str:
        """Return a string representation of the Todo list."""
        lines = [str(todo) for todo in self.todos]
        return "\n".join(lines)


class AddTodosInput(BaseModel):
    """Input model for adding Todo items."""

    tasks: list[str]
    """The task description."""

    index: Optional[int] = None  # noqa: UP045  # type: ignore[reportDeprecated]
    """0-based index at which to insert the new Todo items. If not provided, new items
    will be appended to the end of the list."""


class UpdateTodoInput(BaseModel):
    """Input model for updating a Todo item."""

    index: int
    """The index of the Todo item to update."""

    state: Literal["todo", "in_progress", "done"]
    """The new state of the Todo item."""


TodoToolInput = AddTodosInput | UpdateTodoInput
TodoToolResult = dict[str, bool | list[Todo]]


@final
class TodoTool:
    """A tool to manage a todo list."""

    __name__ = name = "todo_tool"
    description = "A tool to manage a Todo list."

    def __init__(self, session_id: str | None = None) -> None:
        """Initialize the Todo tool with an empty Todo list."""
        self.todo_list = TodoList(todos=[], session_id=session_id)

    @log_tool_call("todo_tool.add_todos")
    def add_todos(self, inp: AddTodosInput, tool_context: ToolContext) -> TodoToolResult:
        """Add new Todo items to the list."""
        insert_idx = inp.index if inp.index is not None else len(self.todo_list)
        self.todo_list.todos[insert_idx:insert_idx] = [Todo(task=task, state="todo") for task in inp.tasks]

        tool_context.state[State.TODO_LIST] = self.todo_list
        return {"success": True, "todos": self.todo_list.todos}

    @log_tool_call("todo_tool.update_todo")
    def update_todo(self, inp: UpdateTodoInput, tool_context: ToolContext) -> TodoToolResult:
        """Update the state of an existing Todo item."""
        if not (0 <= inp.index < len(self.todo_list.todos)):
            msg = f"Index {inp.index} out of range"
            raise IndexError(msg)

        self.todo_list.todos[inp.index].state = inp.state
        tool_context.state[State.TODO_LIST] = self.todo_list

        return {"success": True, "todos": self.todo_list.todos}

    @log_tool_call("todo_tool.clear_todos")
    def clear_todos(self, tool_context: ToolContext) -> TodoToolResult:
        """Clear all Todo items from the list."""
        self.todo_list.todos.clear()
        tool_context.state[State.TODO_LIST] = self.todo_list

        return {"success": True}

    @log_tool_call("todo_tool.delete_todo")
    def delete_todo(self, todo: str, tool_context: ToolContext) -> TodoToolResult:
        """Delete a todo items.

        # Arguments:
            * todo: The task description of the todo item to delete. If multiple items have the same task description,
              only the first one will be deleted.
        """
        val = find_if(lambda t: t.task == todo, self.todo_list.todos)
        if val is None:
            msg = f"Todo item with task '{todo}' not found"
            raise ValueError(msg)

        self.todo_list.todos.remove(val)
        tool_context.state[State.TODO_LIST] = self.todo_list
        return {"success": True}

    @log_tool_call("todo_tool.read_todos")
    def read_todos(self, tool_context: ToolContext) -> list[Todo]:
        """Return the list of Todo items."""
        tool_context.state[State.TODO_LIST] = self.todo_list
        return self.todo_list.todos

    def get_tools(self) -> list[FunctionTool]:
        """Return the list of tools provided by this TodoTool."""
        return [
            FunctionTool(self.add_todos),
            FunctionTool(self.update_todo),
            FunctionTool(self.clear_todos),
            FunctionTool(self.read_todos),
            FunctionTool(self.delete_todo),
        ]
