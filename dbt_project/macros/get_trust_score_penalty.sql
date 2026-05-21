{% macro get_trust_score_penalty() %}
    {% set test_results = run_query(
        "SELECT COUNT(*) as failed_tests FROM test_results.dbt_test_results WHERE status = 'fail'"
    ) %}
    {% set failed_count = test_results.columns[0].values()[0] | default(0) %}
    {% set penalty = (failed_count * 7) %}
    {% set max_penalty = 20 %}
    {% if penalty > max_penalty %}
        {{ return(max_penalty) }}
    {% else %}
        {{ return(penalty) }}
    {% endif %}
{% endmacro %}
