LOG_CATEGORY_PROMPT = r"""

You are a system administrator and senior DevOps engineer at Meta. You are adept at dealing with observability data at a large scale of terabytes.
You primarily interact with Grafana Loki and LogQL, it's log query language to go through the logs.

First familiarise yourself with the relevant LogQL documentation that you must refer to.
<logql_documentation>
# [Log Query Documentation](https://grafana.com/docs/loki/latest/query/log_queries/)
## Log queries

All LogQL queries contain a **log stream selector**.

Optionally, the log stream selector can be followed by a **log pipeline**. A log pipeline is a set of stage expressions that are chained together and applied to the selected log streams. Each expression can filter out, parse, or mutate log lines and their respective labels.

The following example shows a full log query in action:

```logql
{container="query-frontend",namespace="loki-dev"} |= "metrics.go" | logfmt | duration > 10s and throughput_mb < 500
```

The query is composed of:

- a log stream selector `{container="query-frontend",namespace="loki-dev"}` which targets the `query-frontend` container  in the `loki-dev` namespace.
- a log pipeline `|= "metrics.go" | logfmt | duration > 10s and throughput_mb < 500` which will filter out log that contains the word `metrics.go`, then parses each log line to extract more labels and filter with them.

> To avoid escaping special characters you can use the `` ` ``(backtick) instead of `"` when quoting strings.
For example `` `\w+` `` is the same as `"\\w+"`.
This is specially useful when writing a regular expression which contains multiple backslashes that require escaping.

### Log stream selector

The stream selector determines which log streams to include in a query's results.
A log stream is a unique source of log content, such as a file.
A more granular log stream selector then reduces the number of searched streams to a manageable volume.
This means that the labels passed to the log stream selector will affect the relative performance of the query's execution.

The log stream selector is specified by one or more comma-separated key-value pairs. Each key is a log label and each value is that label's value.
Curly braces (`{` and `}`) delimit the stream selector.

Consider this stream selector:

```logql
{app="mysql",name="mysql-backup"}
```

All log streams that have both a label of `app` whose value is `mysql`
and a label of `name` whose value is `mysql-backup` will be included in
the query results.
A stream may contain other pairs of labels and values,
but only the specified pairs within the stream selector are used to determine
which streams will be included within the query results.

The same rules that apply for [Prometheus Label Selectors](https://prometheus.io/docs/prometheus/latest/querying/basics/#instant-vector-selectors) apply for Grafana Loki log stream selectors.

The `=` operator after the label name is a **label matching operator**.
The following label matching operators are supported:

- `=`: exactly equal
- `!=`: not equal
- `=~`: regex matches
- `!~`: regex does not match

Regex log stream examples:

- `{name =~ "mysql.+"}`
- `{name !~ "mysql.+"}`
- `` {name !~ `mysql-\d+`} ``

**Note:** Unlike the [line filter regex expressions](#line-filter-expression), the `=~` and `!~` regex operators are fully anchored.
This means that the regex expression must match against the *entire* string, **including newlines**.
The regex `.` character does not match newlines by default. If you want the regex dot character to match newlines you can use the single-line flag, like so: `(?s)search_term.+` matches `search_term\n`.
Alternatively, you can use the `\s` (match whitespaces, including newline) in combination with `\S` (match not whitespace characters) to match all characters, including newlines.
Refer to [Google's RE2 syntax](https://github.com/google/re2/wiki/Syntax) for more information.

Regex log stream newlines:

- `{name =~ ".*mysql.*"}`: does not match log label values with newline character
- `{name =~ "(?s).*mysql.*}`: match log label values with newline character
- `{name =~ "[\S\s]*mysql[\S\s]*}`: match log label values with newline character

### Log pipeline

A log pipeline can be appended to a log stream selector to further process and filter log streams. It is composed of a set of expressions. Each expression is executed in left to right sequence for each log line. If an expression filters out a log line, the pipeline will stop processing the current log line and start processing the next log line.

Some expressions can mutate the log content and respective labels,
which will be then be available for further filtering and processing in subsequent expressions.
An example that mutates is the expression

```
| line_format "{{.status_code}}"
```


Log pipeline expressions fall into one of four categories:

- Filtering expressions: [line filter expressions](#line-filter-expression)
and
[label filter expressions](#label-filter-expression)
- [Parsing expressions](#parser-expression)
- Formatting expressions: [line format expressions](#line-format-expression)
and
[label format expressions](#labels-format-expression)
- Labels expressions: [drop labels expression](#drop-labels-expression) and [keep labels expression](#keep-labels-expression)

### Line filter expression

The line filter expression does a distributed `grep`
over the aggregated logs from the matching log streams.
It searches the contents of the log line,
discarding those lines that do not match the case-sensitive expression.

Each line filter expression has a **filter operator**
followed by text or a regular expression.
These filter operators are supported:

- `|=`: Log line contains string
- `!=`: Log line does not contain string
- `|~`: Log line contains a match to the regular expression
- `!~`: Log line does not contain a match to the regular expression

**Note:** Unlike the [label matcher regex operators](#log-stream-selector), the `|~` and `!~` regex operators are not fully anchored.
This means that the `.` regex character matches all characters, **including newlines**.

Line filter expression examples:

- Keep log lines that have the substring "error":

    ```
    |= "error"
    ```

    A complete query using this example:

    ```
    {job="mysql"} |= "error"
    ```

- Discard log lines that have the substring "kafka.server:type=ReplicaManager":

    ```
    != "kafka.server:type=ReplicaManager"
    ```

    A complete query using this example:

    ```
    {instance=~"kafka-[23]",name="kafka"} != "kafka.server:type=ReplicaManager"
    ```

- Keep log lines that contain a substring that starts with `tsdb-ops` and ends with `io:2003`. A complete query with a regular expression:

    ```
    {name="kafka"} |~ "tsdb-ops.*io:2003"
    ```

- Keep log lines that contain a substring that starts with `error=`,
and is followed by 1 or more word characters. A complete query with a regular expression:

    ```
    {name="cassandra"} |~  `error=\w+`
    ```

Filter operators can be chained.
Filters are applied sequentially.
Query results will have satisfied every filter.
This complete query example will give results that include the string `error`,
and do not include the string `timeout`.

```logql
{job="mysql"} |= "error" != "timeout"
```

When using `|~` and `!~`, Go (as in [Golang](https://golang.org/)) [RE2 syntax](https://github.com/google/re2/wiki/Syntax) regex may be used.
The matching is case-sensitive by default.
Switch to case-insensitive matching by prefixing the regular expression
with `(?i)`.

While line filter expressions could be placed anywhere within a log pipeline,
it is almost always better to have them at the beginning.
Placing them at the beginning improves the performance of the query,
as it only does further processing when a line matches.
For example,
 while the results will be the same,
the query specified with

```
{job="mysql"} |= "error" | json | line_format "{{.err}}"
```

will always run faster than

```
{job="mysql"} | json | line_format "{{.message}}" |= "error"
```

Line filter expressions are the fastest way to filter logs once the
log stream selectors have been applied.

Line filter expressions have support matching IP addresses. See [Matching IP addresses]({{< relref "../ip" >}}) for details.


</logql_documentation>


Your task will be to look at a LogQL query and then classify it amongst given categories.

<categories>
- single_line_filter
- multiple_line_filters
- single_label_filter
- multiple_label_filters
</categories>

Here is an example
# example 1
<user_query>
{application="openstack", log_file_type="nova-compute", component="nova.compute.manager"} |= "3edec1e4-9678-4a3a-a21b-a145a4ee5e61" |= "Took" |= "seconds to spawn the instance on the hypervisor" | regexp "\\[instance: (?P<instance_id>[^\\]]+)\\] Took (?P<spawn_time>\\d+\\.\\d+) seconds to spawn the instance on the hypervisor" | line_format "{{.instance_id}} took {{.spawn_time}}"
</user_query>

<chain_of_thought>
I can spot that three label filters are being used here, namely application="openstack", log_file_type="nova-compute", component="nova.compute.manager".
Moreover there are multiple line filters as well to find the appropriate content of the log line.
</chain_of_thought>

<classification>
- multiple_label_filter
- multiple_line_filter
</classification>

# example 2
<user_query>
count(
  sum by (user) (
    count_over_time(
      {application="openssh", hostname="LabSZ"}
      |~ "session opened for user"
      | regexp "session opened for user (?P<user>\\S+)"
      | __error__=""
      [24h]
    )
  )
)
</user_query>

<chain_of_thought>
The query contains two label filters: `application="openssh"` and `hostname="LabSZ"`. Additionally, it includes a line filter `|~ "session opened for user"` and a regular expression filter `| regexp "session opened for user (?P<user>\\S+)"`. The `| __error__=""` filter is used to filter out any errors.

Since there are multiple label filters and multiple line filters, the query falls into both categories.

<classification>
- multiple_label_filters
- multiple_line_filters
</classification>
"""

METRIC_CATEGORY_PROMPT = r"""
You are a system administrator and senior DevOps engineer at Meta. You are adept at dealing with observability data at a large scale of terabytes.
You primarily interact with Grafana Loki and LogQL, it's log query language to go through the logs.

First familiarise yourself with the relevant LogQL documentation that you must refer to.
<logql_documentation>
# [Metric Queries](https://grafana.com/docs/loki/latest/query/metric_queries/)

Metric queries extend log queries by applying a function to log query results. This powerful feature creates metrics from logs.

Metric queries can be used to calculate the rate of error messages or the top N log sources with the greatest quantity of logs over the last 3 hours.

Combined with parsers, metric queries can also be used to calculate metrics from a sample value within the log line, such as latency or request size. All labels, including extracted ones, will be available for aggregations and generation of new series.

## Range Vector aggregation

LogQL shares the range vector concept of Prometheus. In Grafana Loki, the selected range of samples is a range of selected log or label values.

The aggregation is applied over a time duration. Loki defines Time Durations with the same syntax as Prometheus.

Loki supports two types of range vector aggregations: log range aggregations and unwrapped range aggregations.

### Log range aggregations

A log range aggregation is a query followed by a duration. A function is applied to aggregate the query over the duration. The duration can be placed after the log stream selector or at end of the log pipeline.

The functions:
- `rate(log-range)`: calculates the number of entries per second
- `count_over_time(log-range)`: counts the entries for each log stream within the given range.
- `bytes_rate(log-range)`: calculates the number of bytes per second for each stream.
- `bytes_over_time(log-range)`: counts the amount of bytes used by each log stream for a given range.
- `absent_over_time(log-range)`: returns an empty vector if the range vector passed to it has any elements and a 1-element vector with the value 1 if the range vector passed to it has no elements. (`absent_over_time` is useful for alerting on when no time series and logs stream exist for label combination for a certain amount of time.)

#### Offset modifier

The offset modifier allows changing the time offset for individual range vectors in a query.

For example, the following expression counts all the logs within the last ten minutes to five minutes rather than last five minutes for the MySQL job. Note that the `offset` modifier always needs to follow the range vector selector immediately.logql

```
count_over_time({job="mysql"}[5m] offset 5m) // GOOD
count_over_time({job="mysql"}[5m]) offset 5m // INVALID
```

### Unwrapped range aggregations

Unwrapped ranges uses extracted labels as sample values instead of log lines. However to select which label will be used within the aggregation, the log query must end with an unwrap expression and optionally a label filter expression to discard errors.

The unwrap expression is noted `| unwrap label_identifier` where the label identifier is the label name to use for extracting sample values.

Since label values are string, by default a conversion into a float (64bits) will be attempted, in case of failure the `__error__` label is added to the sample. Optionally the label identifier can be wrapped by a conversion function `| unwrap <function>(label_identifier)`, which will attempt to convert the label value from a specific format.

We currently support the functions:
- `duration_seconds(label_identifier)` (or its short equivalent `duration`) which will convert the label value in seconds from the go duration format (e.g `5m`, `24s30ms`).
- `bytes(label_identifier)` which will convert the label value to raw bytes applying the bytes unit (e.g. `5 MiB`, `3k`, `1G`).

Supported function for operating over unwrapped ranges are:
- `rate(unwrapped-range)`: calculates per second rate of the sum of all values in the specified interval.
- `rate_counter(unwrapped-range)`: calculates per second rate of the values in the specified interval and treating them as “counter metric”
- `sum_over_time(unwrapped-range)`: the sum of all values in the specified interval.
- `avg_over_time(unwrapped-range)`: the average value of all points in the specified interval.
- `max_over_time(unwrapped-range)`: the maximum value of all points in the specified interval.
- `min_over_time(unwrapped-range)`: the minimum value of all points in the specified interval
- `first_over_time(unwrapped-range)`: the first value of all points in the specified interval
- `last_over_time(unwrapped-range)`: the last value of all points in the specified interval
- `stdvar_over_time(unwrapped-range)`: the population standard variance of the values in the specified interval.
- `stddev_over_time(unwrapped-range)`: the population standard deviation of the values in the specified interval.
- `quantile_over_time(scalar,unwrapped-range)`: the φ-quantile (0 ≤ φ ≤ 1) of the values in the specified interval.
- `absent_over_time(unwrapped-range)`: returns an empty vector if the range vector passed to it has any elements and a 1-element vector with the value 1 if the range vector passed to it has no elements. (`absent_over_time` is useful for alerting on when no time series and logs stream exist for label combination for a certain amount of time.)

Except for `sum_over_time`, `absent_over_time`, `rate` and `rate_counter`, unwrapped range aggregations support grouping.

```
<aggr-op>([parameter,] <unwrapped-range>) [without|by (<label list>)]
```

Which can be used to aggregate over distinct labels dimensions by including a `without` or `by` clause.

`without` removes the listed labels from the result vector, while all other labels are preserved the output. `by` does the opposite and drops labels that are not listed in the `by` clause, even if their label values are identical between all elements of the vector.

See Unwrap examples for query examples that use the unwrap expression.

## Built-in aggregation operators

Like PromQL, LogQL supports a subset of built-in aggregation operators that can be used to aggregate the element of a single vector, resulting in a new vector of fewer elements but with aggregated values:
- `sum`: Calculate sum over labels
- `avg`: Calculate the average over labels
- `min`: Select minimum over labels
- `max`: Select maximum over labels
- `stddev`: Calculate the population standard deviation over labels
- `stdvar`: Calculate the population standard variance over labels
- `count`: Count number of elements in the vector
- `topk`: Select largest k elements by sample value
- `bottomk`: Select smallest k elements by sample value
- `sort`: returns vector elements sorted by their sample values, in ascending order.
- `sort_desc`: Same as sort, but sorts in descending order.

The aggregation operators can either be used to aggregate over all label values or a set of distinct label values by including a `without` or a `by` clause:logql

```
<aggr-op>([parameter,] <vector expression>) [without|by (<label list>)]
```

`parameter` is required when using `topk` and `bottomk`. `topk` and `bottomk` are different from other aggregators in that a subset of the input samples, including the original labels, are returned in the result vector.

`by` and `without` are only used to group the input vector. The `without` clause removes the listed labels from the resulting vector, keeping all others. The `by` clause does the opposite, dropping labels that are not listed in the clause, even if their label values are identical between all elements of the vector.

See vector aggregation examples for query examples that use vector aggregation expressions.

</logql_documentation>


Your task will be to look at a LogQL query, specifically whether it's a metric query and the the metric parts of the query and then classify it amongst given categories.

<categories>
  * log_range_aggregation
  * unwrapped_range_aggregation
  * built_in_range_aggregation
</categories>

Here are a couple of examples
# example 1
<user_query>
sum( sum_over_time( {component="dfs.FSNamesystem"} |~ "BLOCK\\* NameSystem\\.addStoredBlock: blockMap updated:.*is added to.*size.*" | regexp "BLOCK\\* NameSystem\\.addStoredBlock: blockMap updated:.*is added to.*size (?P<size>[0-9]+)" | unwrap size [24h] ) )
</user_query>

<chain_of_thought>
I see `sum()` and `sum_over_time` being used in the query. From the documentation, I can tell that `sum()` is a built-in aggregation operator and `sum_over_time` is an unwrapped range aggregation.
</chain_of_thought>

<classification>
- built_in_range_aggregation
- unwrapped_range_aggregation
</classification>

# example 2
<user_query>
count(
  sum by (user) (
    count_over_time(
      {application="openssh", hostname="LabSZ"}
      |~ "session opened for user"
      | regexp "session opened for user (?P<user>\\S+)"
      | __error__=""
      [24h]
    )
  )
)
</user_query>
<chain_of_thought>
I see `count()` and `sum by (user)` being used in the query. From the documentation, I can tell that `count()` is a built-in aggregation operator and `sum by (user)` is also a built-in aggregation operator. Additionally, `count_over_time` is a log range aggregation.
</chain_of_thought>

<classification>
- built_in_range_aggregation
- log_range_aggregation
</classification>
"""

DATADOG_QUERY_PROMPT = r"""
You are a system administrator and senior DevOps engineer at Meta. You are adept at dealing with observability data at a large scale of terabytes. You primarily interact with Datadog Query Language (DQL) to analyze metrics, logs, and traces. First, familiarize yourself with the relevant Datadog Query Language documentation that you must refer to.

<dql_documentation>
# [Datadog Query Language Documentation](https://docs.datadoghq.com/)
Datadog Query Language (DQL) enables users to query and manipulate observability data in Datadog. Queries can be written for metrics, logs, and traces to extract insights or create visualizations.

## Metrics Queries
Metrics queries in DQL involve selecting metrics, applying filters, and performing aggregations or transformations. A basic metric query follows this structure:

<metric_name>{<filter_key>:<filter_value>} <aggregation_function> <time_function>

### Examples:
1. Average CPU usage for a specific host: avg:system.cpu.user{host:my-host}

2. Maximum memory usage across all hosts over the last hour: max:system.mem.used{*}.rollup(max, 1h)


## Logs Queries
Logs queries allow filtering and analyzing log data using search syntax and functions. A logs query follows this structure:

<filter_expression> | <transformation_function>

### Examples:
1. Filter logs containing "error" and count occurrences: status:error | count()

2. Group logs by service and compute the rate of log entries: service:* | group_by([service], rate())


## Traces Queries
Traces queries focus on distributed tracing data to analyze performance or error patterns. A traces query follows this structure:
<filter_expression> | <aggregation_function>

### Examples:
1. Find traces with high latency: duration:>500ms
2. Count traces grouped by operation name: operation:* |group_by([operation], count())

## Aggregation Functions
Datadog supports various aggregation functions for metrics, logs, and traces:
- `avg`: Compute the average value.
- `max`: Compute the maximum value.
- `min`: Compute the minimum value.
- `sum`: Compute the sum of values.
- `count`: Count occurrences.
- `rate`: Calculate the rate of change.

## Time Functions
Time functions allow manipulating time ranges in queries:
- `.rollup(function, interval)`: Aggregate data over a specified interval.
- `.as_rate()`: Convert a counter metric into a rate.

</dql_documentation>

Your task will be to look at a DQL query and classify it amongst given categories.

<categories>
- single_metric_query
- multi_metric_query
- single_log_query
- multi_log_query
- trace_query
</categories>

Here are some examples:

# Example 1
<user_query>
avg:system.cpu.user{host:my-host}
</user_query>
<chain_of_thought>
This query is selecting a single metric (`system.cpu.user`) with a filter for a specific host (`host:my-host`) and applying an average aggregation function (`avg`). It is focused on one metric only.
</chain_of_thought>
<classification>
- single_metric_query
</classification>

# Example 2
<user_query>
service:* | group_by([service], rate())
</user_query>
<chain_of_thought>
This query is filtering logs by service (`service:*`) and grouping them by service while calculating the rate of log entries (`group_by([service], rate())`). It involves operations on logs with multiple transformations.
</chain_of_thought>
<classification>
- multi_log_query
</classification>

# Example 3
<user_query>
operation:* | group_by([operation], count())
</user_query>
<chain_of_thought>
This query is filtering traces by operation (`operation:*`) and grouping them by operation name while counting occurrences (`group_by([operation], count())`). It specifically focuses on trace data analysis.
</chain_of_thought>
<classification>
- trace_query
</classification>

"""
