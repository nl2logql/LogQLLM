from collections import defaultdict

from datasets import Dataset
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

dataset_path = "nl-logql-dataset-classified-metric-with-variables"

console = Console()


def format_field(label, value, label_color):
    label_text = Text(f"{label}:", style=f"bold {label_color}")
    value_text = Text(str(value), style="yellow")
    return label_text + Text(" ") + value_text


def view_variables_by_application(dataset):
    grouped_data = defaultdict(list)
    for row in dataset:
        if row["variables"]:
            grouped_data[row["application"]].append(
                (row["question"], ", ".join(row["variables"]))
            )

    for app, data in grouped_data.items():
        table = Table(
            title=f"Variables for {app}",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Question", style="cyan", no_wrap=False)
        table.add_column("Variable", style="green")

        for question, variable in data:
            table.add_row(question, variable)

        console.print(table)
        console.print("\n")

    if not grouped_data:
        console.print("[yellow]No variables have been added yet.[/yellow]")


def manually_process_dataset(dataset: Dataset):
    new_variables = list(dataset["variables"])
    i = 0
    while i < len(dataset):
        if not new_variables[i] or (
            isinstance(new_variables[i], list) and not any(new_variables[i])
        ):
            row = dataset[i]

            panel_content = Text()
            panel_content.append(
                format_field("Application", row["application"], "cyan")
            )
            panel_content.append("\n")
            panel_content.append(
                format_field("Question", row["question"], "cyan")
            )
            panel_content.append("\n")
            panel_content.append(
                format_field(
                    "LogQL Query (raw)", repr(row["logql_query"]), "cyan"
                )
            )
            panel_content.append("\n")
            panel_content.append(
                format_field("Query Result", row["query_result"], "cyan")
            )
            panel_content.append("\n")
            panel_content.append(
                format_field("Line Filter", row["line_filter"], "cyan")
            )
            panel_content.append("\n")
            panel_content.append(
                format_field("Label Filter", row["label_filter"], "cyan")
            )

            console.print(
                Panel(
                    panel_content,
                    title=f"[bold magenta]Row {i + 1}[/bold magenta]",
                    expand=False,
                    border_style="blue",
                )
            )

            while True:
                user_input = console.input(
                    "[bold green]Enter the variables for this row as comma-separated values (or 'skip' to skip, 'quit' to exit, 'view' to see variables): [/bold green]"
                )

                if user_input.lower() == "quit":
                    # Update the dataset with new variables before exiting
                    updated_dataset = dataset.remove_columns(["variables"])
                    updated_dataset = updated_dataset.add_column(
                        name="variables", column=new_variables
                    )
                    return updated_dataset  # Exit the function entirely
                elif user_input.lower() == "skip":
                    break  # Break the inner loop to move to the next row
                elif user_input.lower() == "view":
                    view_variables_by_application(dataset)
                    continue  # Continue the inner loop, asking for input again

                try:
                    variables_list = [
                        var.strip()
                        for var in user_input.split(",")
                        if var.strip()
                    ]
                    new_variables[i] = variables_list
                    break  # Break the inner loop to move to the next row
                except Exception as e:
                    console.print(
                        Panel(
                            f"[bold red]Error processing input:[/bold red]\n{str(e)}",
                            title="Error",
                            border_style="red",
                        )
                    )
                    console.print("[yellow]Please try again.[/yellow]")

        # Increment i after processing each row, regardless of whether it was skipped or filled
        i += 1

    # Update the dataset with new variables
    updated_dataset = dataset.remove_columns(["variables"])
    updated_dataset = updated_dataset.add_column(
        name="variables", column=new_variables
    )

    return updated_dataset


# Load the original dataset
dataset = Dataset.load_from_disk(dataset_path)

# Process the dataset
updated_dataset = manually_process_dataset(dataset)

# Save the final updated dataset
df = updated_dataset.to_pandas()
# print(df["variables"][3])
Dataset.from_pandas(df).save_to_disk(dataset_path)
console.print(
    "[bold green]Processing complete. Final dataset saved.[/bold green]"
)
