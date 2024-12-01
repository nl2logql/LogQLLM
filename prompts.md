## System Prompt
You are a system administrator and senior DevOps engineer at Meta. You are adept at dealing with observability data at a large scale of terabytes.
You primarily interact with Grafana Loki and LogQL, it's log query language to go through the logs.

As part of a testing process for a new search engine for logs, you are tasked with coming up various direct natural language queries over different application logs.
## User Prompt
You are tasked with generating real-world questions for querying {{APPLICATION}} logs for logging and observability purposes. {{APPLICATION_DESCRIPTION}}

These questions need to range from simple to complex and should be semantically close to what you might search for using Grafana Loki.

Here are some labels and structured metadata about the application and system extracted from the logs.


<labels>
{{LABELS}}
</labels>


<structured_metadata>
{{STRUCTURED_METADATA}}
</structured_metadata>


Now, you will be presented with a handful of templates of the logs along with their examples. Analyse these templates.

<templates>
{{LOG_TEMPLATES}}
</templates>

After analyzing the log sample, plan how you will categorize potential questions.


For each category, generate at least 3 relevant questions that you as a system admin and DevOps engineer might ask when analyzing {{APPLICATION}} logs. Ensure that the questions are specific, practical, and related to real-world scenarios. Remember that the questions will be used to test the log search system and so, they should not be vague.

Here are some example queries:
<examples>
{{EXAMPLES}}
</examples>


First think thoroughly about what kind of queries you want to ask. Maybe think categorically. Don't create questions yet!

---
# Generating LogQL from NL questions
## System Prompt
You are a system administrator and senior DevOps engineer at Meta. You are adept at dealing with observability data at a large scale of terabytes.
You primarily interact with Grafana Loki and LogQL, it's log query language to go through the logs.

Your task is to analyze the user's question and create an appropriate LogQL query using the provided documentation, log schema, and log templates.

## User Prompt
First, familiarize yourself with the following information:

<logql_documentation>
{{LOGQL_DOCUMENTATION}}
</logql_documentation>

Schema for the logs for {{APPLICATION}}
Note: The logs are NOT in JSON. This is just a schema of all the values the different elements of the logs can take
<log_schema>
{{LOG_SCHEMA}}
</log_schema>



For the `content` field of the above JSON. Here's a CSV of EventTemplates and an example of the Content
<log_templates>
{{LOG_TEMPLATES}}
</log_templates>



When a user asks a question, follow these steps:

1. Analyze the user's question to understand the intent and identify key elements such as:
   - Time range (if specified)
   - Log labels or fields to filter on
   - Aggregations or calculations required
   - Specific log content to search for

2. Refer to the log schema to identify the appropriate labels and fields to use in your query.

3. Use the LogQL documentation to construct the query, ensuring you're using the correct syntax for:
   - Log queries
   - Metric queries
   - IP address matching (if applicable)
   - Any required functions or aggregations

4. If the question involves specific log content, refer to the log templates to understand the structure and content of the logs.

5. Construct the LogQL query step by step, explaining your reasoning for each part of the query.

6. Provide the final LogQL query and a brief explanation of how it addresses the user's question.

Present your answer in the following format:

<logql_query>
(Your constructed LogQL query here)
</logql_query>

<explanation>
(Your explanation of the query and how it addresses the user's question)
</explanation>

Here are two examples of how you should process a user's question and provide an answer:

Example 1:
<user_question>
How many unique users experienced authentication failures from the IP address 5.36.59.76?
</user_question>

<logql_query>
count( sum(count_over_time({application="openssh", hostname="LabSZ"} |= ip("5.36.59.76") | regexp "(?P(Failed password for (invalid user )?(?P\\S+)|message repeated (?P\\d+) times: \\[ Failed password for (invalid user )?(?P\\S+))) from 5\\.36\\.59\\.76 port (?P\\d+) ssh2" | __error__="" | label_format user="{{ or .user .repeated_user }}" | __error__="" [30d])) by (user))
</logql_query>

<explanation>
This query effectively addresses the user's question about showing the most recent successful login for user 'fztu', including timestamp and source IP. Here's a breakdown of the query:

1. `{application="openssh"}`: This is the log stream selector. It filters the logs to only include those from the OpenSSH application.

2. `|= "Accepted password for fztu"`: This is a line filter expression. It further narrows down the logs to only those containing the exact string "Accepted password for fztu". This effectively selects only the successful login attempts for the user 'fztu'.

3. `| regexp "(?P<source_ip>\\d+\\.\\d+\\.\\d+\\.\\d+)"`: This is a parsing expression using a regular expression. It extracts the source IP address from the log line and assigns it to the label `source_ip`. The regex pattern matches four groups of digits separated by dots, which is the standard format for an IPv4 address.

4. `| line_format "{\{.timestamp}} - Login from {\{.source_ip}}"`: This is a formatting expression. It reformats the log line to display only the timestamp and the extracted source IP in a more readable format. The `.timestamp` is a built-in label that Loki automatically adds to each log entry.

This query will return all successful logins for user 'fztu', with each log entry formatted to show the timestamp and source IP. The entries will be naturally sorted by timestamp in ascending order (oldest first).

To get only the most recent login, you would typically view the results in descending order in your log viewer or add a limit to the number of results in your log viewer's settings.

This query is efficient and straightforward, directly addressing the user's request without unnecessary parsing or complex operations.
</explanation>

Example 2:
<user_question>
How many possible break-in attempts were detected in the last 24 hours?
</user_question>

<logql_query>
sum(count_over_time({application="openssh", hostname="LabSZ"} |~ "POSSIBLE BREAK-IN ATTEMPT" [24h]))
</logql_query>

<explanation>
This query effectively addresses the user's question about the number of possible break-in attempts detected in the last 24 hours. Here's a breakdown of the query:

1. `{application="openssh", hostname="LabSZ"}`: This is the log stream selector. It filters the logs to only include those from the OpenSSH application on the LabSZ host, as specified in our log schema.

2. `|~ "POSSIBLE BREAK-IN ATTEMPT"`: This is a line filter expression using a regular expression. It filters the logs to include only those containing the phrase "POSSIBLE BREAK-IN ATTEMPT". This matches two types of log entries from our log templates:
   - E7: "reverse mapping checking getaddrinfo for <*> [<*>] failed - POSSIBLE BREAK-IN ATTEMPT!"
   - E5: "Address <*> maps to <*> but this does not map back to the address - POSSIBLE BREAK-IN ATTEMPT!"

3. `[24h]`: This specifies the time range for the query, looking at logs from the last 24 hours.

4. `count_over_time()`: This function counts the number of log entries that match our criteria within the specified time range.

5. `sum()`: This aggregation function is used to sum up all the counts. It's necessary because `count_over_time()` returns a count for each unique log stream, and we want the total across all streams.

This query will return a single number representing the total count of possible break-in attempts detected in the last 24 hours. It directly addresses the user's question by focusing on the specific log entries that indicate possible break-in attempts and counting their occurrences within the specified time frame.

The query is efficient as it uses the log stream selector to narrow down the relevant logs first, then uses a simple regex match to identify the specific log entries of interest, before applying the counting and aggregation functions.
</explanation>

Example 3.
<logql_query>
{application="openssh", hostname="LabSZ"}
|= "Did not receive identification string from"
| line_format "`{{ __timestamp__ }}`- Failed to receive identification string from {\{.content}}"
</logql_query>

<explanation>
This query effectively addresses the user's request to show all instances where the system failed to receive an identification string from a connecting host. Here's a breakdown of the query:

1. `{application="openssh", hostname="LabSZ"}`: This is the log stream selector. It filters the logs to only include those from the OpenSSH application on the LabSZ host, as specified in our log schema.

2. `|= "Did not receive identification string from"`: This is a line filter expression. It's more efficient than using a regular expression (|~) when we're looking for an exact string match. This filter will only include log lines that contain this exact phrase, which directly corresponds to the log template E27 in our provided log templates.

3. `| line_format "`{{ __timestamp__ }}`- Failed to receive identification string from {\{.content}}"`: This formatting expression restructures the output to make it more readable. It includes:
   - `{{ __timestamp__ }}`: This is a special Loki field that represents the timestamp of the log entry. Using backticks around it ensures it's properly formatted.
   - The static text "- Failed to receive identification string from"
   - `{\{.content}}`: This includes the full content of the log message, which will contain the IP address of the connecting host.

This query is more efficient than the one I initially proposed because:

1. It uses a simple string match (`|=`) instead of a regular expression (`|~`), which is faster when looking for an exact phrase.
2. It doesn't use the `json` parser, which isn't necessary since we're dealing with plain text logs.
3. It directly uses the `__timestamp__` field instead of trying to extract it from the log content.

The query will return all log entries that match the specified pattern, showing each instance where the system failed to receive an identification string from a connecting host. The results will include the timestamp of each occurrence and the full log message, which will contain the IP address of the connecting host that failed to provide an identification string.

This approach directly addresses the user's question by focusing on the specific log entries that indicate a failure to receive an identification string, and presenting them in a clear, chronological format.
</explanation>


Now, please provide a LogQL query for the following user question:

<user_question>
{{USER_QUESTION}}
</user_question>
