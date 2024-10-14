from fasthtml.common import *

app, rt = fast_app()

BACKEND_URL = (
    "http://localhost:8000"  # Replace with your backend URL if different
)


@rt("/")
def get():
    return Titled(
        "LogQL Dataset Manager",
        Div(
            H2("Add New Entry"),
            Form(id="add-entry-form")(
                Label("Application", Input(name="application")),
                Label("Category", Input(name="category")),
                Label("Question", Input(name="question")),
                Label("LogQL Query", Textarea(name="logql_query")),
                Label("Query Explanation", Textarea(name="query_explanation")),
                Label("Query Result", Textarea(name="query_result")),
                Label(
                    "Log Category Result", Textarea(name="log_category_result")
                ),
                Label("Line Filter", Input(name="line_filter")),
                Label("Label Filter", Input(name="label_filter")),
                Label("Metric Category", Input(name="metric_category")),
                Label("Variables", Input(name="variables")),
                Button("Add Entry", type="submit"),
            ),
            H2("Existing Entries"),
            Div(
                Label(
                    "Filter by Application",
                    Select(id="application-filter")(
                        Option("None", value="None", selected="selected"),
                    ),
                ),
                Label(
                    "Filter by Category",
                    Select(id="category-filter")(
                        Option("None", value="None", selected="selected"),
                    ),
                ),
                Button("Apply Filters", id="apply-filters"),
            ),
            Div(id="entries-table"),
            Div(id="pagination-controls"),
            # Add the button to view all entries
            P(A("View All Entries", href="/view_entries", cls="button")),
            # Edit Modal
            Div(id="edit-modal", cls="modal")(
                Div(cls="modal-content")(
                    H2("Edit Entry"),
                    Form(id="edit-entry-form")(
                        Input(type="hidden", id="edit-id", name="id"),
                        Label(
                            "Application",
                            Input(id="edit-application", name="application"),
                        ),
                        Label(
                            "Category",
                            Input(id="edit-category", name="category"),
                        ),
                        Label(
                            "Question",
                            Input(id="edit-question", name="question"),
                        ),
                        Label(
                            "LogQL Query",
                            Textarea(id="edit-logql_query", name="logql_query"),
                        ),
                        Label(
                            "Query Explanation",
                            Textarea(
                                id="edit-query_explanation",
                                name="query_explanation",
                            ),
                        ),
                        Label(
                            "Query Result",
                            Textarea(
                                id="edit-query_result", name="query_result"
                            ),
                        ),
                        Label(
                            "Log Category Result",
                            Textarea(
                                id="edit-log_category_result",
                                name="log_category_result",
                            ),
                        ),
                        Label(
                            "Line Filter",
                            Input(id="edit-line_filter", name="line_filter"),
                        ),
                        Label(
                            "Label Filter",
                            Input(id="edit-label_filter", name="label_filter"),
                        ),
                        Label(
                            "Metric Category",
                            Input(
                                id="edit-metric_category",
                                name="metric_category",
                            ),
                        ),
                        Label(
                            "Variables",
                            Input(id="edit-variables", name="variables"),
                        ),
                        Button("Save Changes", type="submit"),
                        Button(
                            "Cancel", type="button", onclick="closeEditModal()"
                        ),
                    ),
                )
            ),
        ),
        Style("""
            .modal {
                display: none;
                position: fixed;
                z-index: 1;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                overflow: auto;
                background-color: rgba(0,0,0,0.4);
            }
            .modal-content {
                background-color: #fefefe;
                margin: 15% auto;
                padding: 20px;
                border: 1px solid #888;
                width: 80%;
            }
            #pagination-controls {
                margin-top: 20px;
                text-align: center;
            }
            #pagination-controls button {
                margin: 0 5px;
            }
            .button {
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                margin-top: 20px;
            }
            .button:hover {
                background-color: #0056b3;
            }
        """),
        Script(f"""
            const BACKEND_URL = "{BACKEND_URL}";
            let currentPage = 1;
            let itemsPerPage = 100;
            let currentApplicationFilter = "None";
            let currentCategoryFilter = "None";

            document.getElementById('add-entry-form').addEventListener('submit', function(e) {{
                e.preventDefault();
                const formData = new FormData(this);
                const entry = Object.fromEntries(formData);

                fetch(`${{BACKEND_URL}}/add_entry`, {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(entry),
                }})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message);
                    this.reset();
                    loadEntries();
                    populateFilters();
                }})
                .catch((error) => {{
                    console.error('Error:', error);
                    alert('An error occurred while adding the entry.');
                }});
            }});

            function loadEntries() {{
                const url = new URL(`${{BACKEND_URL}}/entries`);
                url.searchParams.append('page', currentPage);
                url.searchParams.append('items_per_page', itemsPerPage);
                if (currentApplicationFilter !== "None") {{
                    url.searchParams.append('application_filter', currentApplicationFilter);
                }}
                if (currentCategoryFilter !== "None") {{
                    url.searchParams.append('category_filter', currentCategoryFilter);
                }}

                fetch(url)
                    .then(response => response.json())
                    .then(data => {{
                        const table = document.createElement('table');
                        table.innerHTML = `
                            <tr>
                                <th>ID</th>
                                <th>Application</th>
                                <th>Category</th>
                                <th>Question</th>
                                <th>LogQL Query</th>
                                <th>Query Explanation</th>
                                <th>Query Result</th>
                                <th>Actions</th>
                            </tr>
                        `;
                        data.entries.forEach(entry => {{
                            const row = table.insertRow();
                            row.innerHTML = `
                                <td>${{entry.id}}</td>
                                <td>${{entry.application}}</td>
                                <td>${{entry.category}}</td>
                                <td>${{entry.question}}</td>
                                <td>${{entry.logql_query}}</td>
                                <td>${{entry.query_explanation}}</td>
                                <td>${{entry.query_result}}</td>
                                <td>
                                    <button onclick="editEntry(${{entry.id}})">Edit</button>
                                    <button onclick="deleteEntry(${{entry.id}})">Delete</button>
                                </td>
                            `;
                        }});
                        document.getElementById('entries-table').innerHTML = '';
                        document.getElementById('entries-table').appendChild(table);

                        updatePaginationControls(data.current_page, data.total_pages);
                    }});
            }}

            function updatePaginationControls(currentPage, totalPages) {{
                const controls = document.getElementById('pagination-controls');
                controls.innerHTML = `
                    <button onclick="changePage(1)" ${{currentPage === 1 ? 'disabled' : ''}}>First</button>
                    <button onclick="changePage(${{currentPage - 1}})" ${{currentPage === 1 ? 'disabled' : ''}}>Previous</button>
                    <span>Page ${{currentPage}} of ${{totalPages}}</span>
                    <button onclick="changePage(${{currentPage + 1}})" ${{currentPage === totalPages ? 'disabled' : ''}}>Next</button>
                    <button onclick="changePage(${{totalPages}})" ${{currentPage === totalPages ? 'disabled' : ''}}>Last</button>
                `;
            }}

            function changePage(newPage) {{
                currentPage = newPage;
                loadEntries();
            }}

            function populateFilters() {{
                fetch(`${{BACKEND_URL}}/entries`)
                    .then(response => response.json())
                    .then(data => {{
                        const applications = new Set(data.entries.map(entry => entry.application));
                        const categories = new Set(data.entries.map(entry => entry.category));

                        const applicationFilter = document.getElementById('application-filter');
                        const categoryFilter = document.getElementById('category-filter');

                        applicationFilter.innerHTML = '<option value="None" selected>None</option>';
                        categoryFilter.innerHTML = '<option value="None" selected>None</option>';

                        applications.forEach(app => {{
                            const option = document.createElement('option');
                            option.value = app;
                            option.textContent = app;
                            applicationFilter.appendChild(option);
                        }});

                        categories.forEach(cat => {{
                            const option = document.createElement('option');
                            option.value = cat;
                            option.textContent = cat;
                            categoryFilter.appendChild(option);
                        }});
                    }});
            }}

            document.getElementById('apply-filters').addEventListener('click', function() {{
                currentApplicationFilter = document.getElementById('application-filter').value;
                currentCategoryFilter = document.getElementById('category-filter').value;
                currentPage = 1;  // Reset to first page when applying new filters
                loadEntries();
            }});

            function editEntry(id) {{
                fetch(`${{BACKEND_URL}}/entries`)
                    .then(response => response.json())
                    .then(data => {{
                        const entry = data.entries.find(e => e.id === id);
                        document.getElementById('edit-id').value = entry.id;
                        document.getElementById('edit-application').value = entry.application;
                        document.getElementById('edit-category').value = entry.category;
                        document.getElementById('edit-question').value = entry.question;
                        document.getElementById('edit-logql_query').value = entry.logql_query;
                        document.getElementById('edit-query_explanation').value = entry.query_explanation;
                        document.getElementById('edit-query_result').value = entry.query_result;
                        document.getElementById('edit-modal').style.display = 'block';
                    }});
            }}

            function closeEditModal() {{
                document.getElementById('edit-modal').style.display = 'none';
            }}

            document.getElementById('edit-entry-form').addEventListener('submit', function(e) {{
                e.preventDefault();
                const formData = new FormData(this);
                const entry = Object.fromEntries(formData);
                const id = entry.id;
                delete entry.id;

                fetch(`${{BACKEND_URL}}/edit_entry/${{id}}`, {{
                    method: 'PUT',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify(entry),
                }})
                .then(response => response.json())
                .then(data => {{
                    alert(data.message);
                    closeEditModal();
                    loadEntries();
                    populateFilters();
                }})
                .catch((error) => {{
                    console.error('Error:', error);
                    alert('An error occurred while editing the entry.');
                }});
            }});

            function deleteEntry(id) {{
                if (confirm('Are you sure you want to delete this entry?')) {{
                    fetch(`${{BACKEND_URL}}/delete_entry/${{id}}`, {{ method: 'DELETE' }})
                        .then(response => response.json())
                        .then(data => {{
                            alert(data.message);
                            loadEntries();
                            populateFilters();
                        }});
                }}
            }}

            // Initial load
            populateFilters();
            loadEntries();
        """),
    )


@rt("/view_entries")
def view_entries():
    return Titled(
        "View All Entries",
        Div(
            H2("All Entries"),
            Div(id="all-entries-table"),
            A("Back to Main Page", href="/"),
        ),
        Script("""
            const BACKEND_URL = "http://localhost:8000";
            function loadAllEntries() {
                fetch(`${BACKEND_URL}/all_entries`)
                    .then(response => response.json())
                    .then(data => {
                        const table = document.createElement('table');
                        table.innerHTML = `
                            <tr>
                                <th>ID</th>
                                <th>Application</th>
                                <th>Category</th>
                                <th>Question</th>
                                <th>LogQL Query</th>
                                <th>Query Explanation</th>
                                <th>Query Result</th>
                                <th>Log Category Result</th>
                                <th>Line Filter</th>
                                <th>Label Filter</th>
                                <th>Metric Category</th>
                                <th>Variables</th>
                            </tr>
                        `;
                        data.entries.forEach(entry => {
                            const row = table.insertRow();
                            row.innerHTML = `
                                <td>${entry.id}</td>
                                <td>${entry.application}</td>
                                <td>${entry.category}</td>
                                <td>${entry.question}</td>
                                <td>${entry.logql_query}</td>
                                <td>${entry.query_explanation}</td>
                                <td>${entry.query_result}</td>
                                <td>${JSON.stringify(entry.log_category_result)}</td>
                                <td>${entry.line_filter}</td>
                                <td>${entry.label_filter}</td>
                                <td>${entry.metric_category?.join(', ')}</td>
                                <td>${entry.variables?.join(', ')}</td>
                            `;
                        });
                        document.getElementById('all-entries-table').innerHTML = '';
                        document.getElementById('all-entries-table').appendChild(table);
                    });
            }

            // Load all entries when the page loads
            loadAllEntries();
        """),
    )


serve()
