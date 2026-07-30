from datetime import datetime
from html import escape
from pathlib import Path

from src.models import EvaluationStatus, ModelSummary, TestResult
from src.report_analytics import (
    build_model_summaries,
    get_fastest_model,
    get_highest_scoring_model,
)


class HtmlReporter:
    """Writes AI test results to a styled HTML report."""

    def __init__(self, report_path: Path) -> None:
        self.report_path = report_path

    def write(self, results: list[TestResult]) -> None:
        self.report_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        generated_at = datetime.now().astimezone().strftime(
            "%B %d, %Y at %I:%M:%S %p %Z"
        )

        passed = sum(
            result.status == EvaluationStatus.PASS
            for result in results
        )

        expected_failures = sum(
            result.status == EvaluationStatus.XFAIL
            for result in results
        )

        unexpected_failures = sum(
            result.status == EvaluationStatus.FAIL
            for result in results
        )

        errors = sum(
            result.status == EvaluationStatus.ERROR
            for result in results
        )

        total = len(results)

        total_estimated_cost_usd = sum(
            result.estimated_cost_usd
            for result in results
        )

        pass_rate_percent = (
            passed / total * 100
            if total
            else 0.0
        )

        model_summaries = build_model_summaries(results)

        fastest_model = get_fastest_model(model_summaries)
        highest_scoring_model = get_highest_scoring_model(
            model_summaries
        )

        comparison_rows = "\n".join(
            self._create_model_comparison_row(
                summary=summary,
                fastest_model=fastest_model,
                highest_scoring_model=highest_scoring_model,
            )
            for summary in model_summaries
        )

        result_rows = "\n".join(
            self._create_result_row(result)
            for result in results
        )

        highest_scoring_name = (
            highest_scoring_model.model
            if highest_scoring_model
            else "N/A"
        )

        fastest_model_name = (
            fastest_model.model
            if fastest_model
            else "N/A"
        )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>AI Test Lab Report</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 32px;
            background-color: #f4f6f8;
            color: #1f2937;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        h1 {{
            margin-bottom: 8px;
        }}

        h2 {{
            margin-top: 36px;
            margin-bottom: 16px;
        }}

        .subtitle {{
            margin-top: 0;
            margin-bottom: 6px;
            color: #64748b;
            font-size: 17px;
        }}

        .generated-at {{
            margin-top: 0;
            margin-bottom: 28px;
            color: #64748b;
            font-size: 14px;
        }}
        
            
        .result-details {{
        min-width: 140px;
        }}

        .result-details summary{{
                color: #2563eb;
            font-weight: bold;
            cursor: pointer;
            user-select: none;
        }}

        .result-details summary:hover {{
                text-decoration: underline;
        }}

        .result-details[open] {{
                min-width: 520px;
        }}

        .details-content {{
                margin-top: 14px;
            padding: 18px;
            background-color: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            white-space: normal;
        }}

        .detail-section {{
                margin-bottom: 20px;
        }}

        .detail-section:last-child {{
                margin-bottom: 0;
        }}

        .detail-section h3 {{
                margin: 0 0 10px;
            font-size: 16px;
        }}

        .detail-grid {{
                display: grid;
            grid-template-columns: minmax(130px, 180px) 1fr;
            gap: 8px 16px;
            margin: 0;
        }}

        .detail-grid dt {{
                color: #64748b;
            font-weight: bold;
        }}

        .detail-grid dd {{
                margin: 0;
            overflow-wrap: anywhere;
        }}

        .detail-section pre {{
                max-width: 700px;
            max-height: 360px;
            margin: 0;
            padding: 14px;
            overflow: auto;
            background-color: #111827;
            color: #f9fafb;
            border-radius: 7px;
            font-family: Consolas, Monaco, monospace;
            font-size: 13px;
            line-height: 1.5;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }}

        .detail-section code {{
                padding: 2px 6px;
            background-color: #e2e8f0;
            border-radius: 4px;
            font-family: Consolas, Monaco, monospace;
        }}

        .metrics-grid {{
                grid-template-columns:
                minmax(150px, 190px)
                minmax(90px, 1fr)
                minmax(150px, 190px)
                minmax(90px, 1fr);
        }}

        @media (max-width: 900px) {{
                .result-details[open] {{
                min-width: 360px;
            }}
        
                .detail-grid,
                .metrics-grid {{
                grid-template-columns: 1fr;
            }}
        
                .detail-grid dt {{
                margin-top: 8px;
            }}
        }}
       

        .summary {{
            display: grid;
            grid-template-columns: repeat(
                7,
                minmax(140px, 1fr)
            );
            gap: 16px;
            margin: 24px 0;
        }}

        .summary-card {{
            padding: 18px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        .summary-label {{
            display: block;
            margin-bottom: 8px;
            color: #6b7280;
            font-size: 14px;
        }}

        .summary-value {{
            font-size: 28px;
            font-weight: bold;
        }}
        
        .xfail-value {{
            color: #b45309;
       }}
       
       .status-xfail {{
           background-color: #fef3c7;
            color: #92400e;
       }}

        .passed-value {{
            color: #15803d;
        }}

        .failed-value {{
            color: #b91c1c;
        }}

        .error-value {{
            color: #c2410c;
        }}

        .highlight-grid {{
            display: grid;
            grid-template-columns: repeat(
                2,
                minmax(240px, 1fr)
            );
            gap: 16px;
            margin: 24px 0;
        }}

        .highlight-card {{
            padding: 18px;
            background-color: white;
            border-left: 5px solid #2563eb;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        .highlight-label {{
            display: block;
            margin-bottom: 8px;
            color: #64748b;
            font-size: 14px;
        }}

        .highlight-value {{
            font-size: 18px;
            font-weight: bold;
            overflow-wrap: anywhere;
        }}

        .table-wrapper {{
            overflow-x: auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background-color: white;
        }}

        th,
        td {{
            padding: 14px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
            white-space: nowrap;
        }}

        th {{
            background-color: #1f2937;
            color: white;
            font-size: 14px;
        }}

        tbody tr:hover {{
            background-color: #f9fafb;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .model-name {{
            font-weight: bold;
        }}

        .numeric {{
            text-align: right;
        }}

        .pass-rate {{
            font-weight: bold;
        }}

        .pass-rate-high {{
            color: #15803d;
        }}

        .pass-rate-medium {{
            color: #b45309;
        }}

        .pass-rate-low {{
            color: #b91c1c;
        }}

        .badge {{
            display: inline-block;
            margin-left: 6px;
            padding: 4px 8px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: bold;
        }}

        .badge-score {{
            background-color: #dbeafe;
            color: #1d4ed8;
        }}

        .badge-fast {{
            background-color: #fef3c7;
            color: #92400e;
        }}

        .status {{
            display: inline-block;
            min-width: 58px;
            padding: 5px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: bold;
            text-align: center;
        }}

        .status-pass {{
            background-color: #dcfce7;
            color: #166534;
        }}

        .status-fail {{
            background-color: #fee2e2;
            color: #991b1b;
        }}

        .status-error {{
            background-color: #ffedd5;
            color: #9a3412;
        }}

        @media (max-width: 1000px) {{
            .summary {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}

        @media (max-width: 700px) {{
            body {{
                padding: 16px;
            }}

            .summary,
            .highlight-grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <h1>AI Test Lab Report</h1>

        <p class="subtitle">
            Automated multi-model LLM evaluation results
        </p>

        <p class="generated-at">
            <strong>Generated:</strong>
            {escape(generated_at)}
        </p>

        <section class="summary">
            <div class="summary-card">
                <span class="summary-label">Total Evaluations</span>
                <span class="summary-value">{total}</span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Passed</span>
                <span class="summary-value passed-value">
                    {passed}
                </span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Expected Failures</span>
                <span class="summary-value xfail-value">
                    {expected_failures}
                </span>
            </div>
            
            <div class="summary-card">
                <span class="summary-label">Unexpected Failures</span>
                <span class="summary-value failed-value">
                    {unexpected_failures}
                </span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Errors</span>
                <span class="summary-value error-value">
                    {errors}
                </span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Overall Pass Rate</span>
                <span class="summary-value">
                    {pass_rate_percent:.1f}%
                </span>
            </div>
            <div class="summary-card">
                <span class="summary-label">Total Estimated Cost</span>
                <span class="summary-value">
                    ${total_estimated_cost_usd:.6f}
                </span>
            </div>
            
        </section>

        <section class="highlight-grid">
            <div class="highlight-card">
                <span class="highlight-label">
                    Top Ranked Model
                </span>

                <span class="highlight-value">
                    {escape(highest_scoring_name)}
                </span>
            </div>

            <div class="highlight-card">
                <span class="highlight-label">
                    Fastest Average Response
                </span>

                <span class="highlight-value">
                    {escape(fastest_model_name)}
                </span>
            </div>
        </section>

        <h2>Model Comparison</h2>

        <div class="table-wrapper">
    <table>
        <thead>
            <tr>
                <th>Provider</th>
                <th>Model</th>
                <th class="numeric">Passed</th>
                <th class="numeric">Expected Failures</th>
                <th class="numeric">Unexpected Failures</th>
                <th class="numeric">Errors</th>
                <th class="numeric">Total</th>
                <th class="numeric">Pass Rate</th>
                <th class="numeric">Avg Response</th>
                <th class="numeric">Avg Generation</th>
                <th class="numeric">Avg Speed</th>
                <th class="numeric">Avg Output Tokens</th>
                <th class="numeric">Total Cost</th>
                <th class="numeric">Avg Cost</th>
            </tr>
        </thead>

                <tbody>
                    {comparison_rows}
                </tbody>
            </table>
        </div>

        <h2>Individual Test Results</h2>

        <div class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Test ID</th>
                        <th>Provider</th>
                        <th>Model</th>
                        <th>Status</th>
                        <th class="numeric">Response Time</th>
                        <th class="numeric">Estimated Cost</th>
                        <th>Details</th>
                    </tr>
                </thead>

                <tbody>
                    {result_rows}
                </tbody>
            </table>
        </div>
    </main>
</body>
</html>
"""

        self.report_path.write_text(
            html_content,
            encoding="utf-8",
        )

    @staticmethod
    def _create_model_comparison_row(
            summary: ModelSummary,
            fastest_model: ModelSummary | None,
            highest_scoring_model: ModelSummary | None,
    ) -> str:
        badges: list[str] = []

        if (
                highest_scoring_model is not None
                and summary.model == highest_scoring_model.model
        ):
            badges.append(
                '<span class="badge badge-score">'
                "Highest score"
                "</span>"
            )

        if (
                fastest_model is not None
                and summary.model == fastest_model.model
        ):
            badges.append(
                '<span class="badge badge-fast">'
                "Fastest"
                "</span>"
            )

        badge_html = "".join(badges)

        pass_rate_class = HtmlReporter._get_pass_rate_class(
            summary.pass_rate_percent
        )

        return f"""

<tr>
    <td>{escape(summary.provider)}</td>
    
    <td class="model-name">
        {escape(summary.model)}
        {badge_html}
    </td>



    <td class="numeric">{summary.passed}</td>
    <td class="numeric">{summary.expected_failures}</td>
    <td class="numeric">{summary.unexpected_failures}</td>
    <td class="numeric">{summary.errors}</td>
    <td class="numeric">{summary.total}</td>

    <td class="numeric pass-rate {pass_rate_class}">
        {summary.pass_rate_percent:.2f}%
    </td>

    <td class="numeric">
        {summary.average_response_time_seconds:.3f} s
    </td>

    <td class="numeric">
        {summary.average_generation_latency_seconds:.3f} s
    </td>

    <td class="numeric">
        {summary.average_generation_tokens_per_second:.2f} tok/s
    </td>
    
    <td class="numeric">
        {summary.average_output_tokens:.1f}
    </td>
        
    <td class="numeric">
        ${summary.total_estimated_cost_usd:.6f}
    </td>
        
    <td class="numeric">
        ${summary.average_estimated_cost_usd:.6f}
    </td>
</tr>               
 
"""

    @staticmethod
    def _get_pass_rate_class(pass_rate_percent: float) -> str:
        if pass_rate_percent >= 80:
            return "pass-rate-high"

        if pass_rate_percent >= 60:
            return "pass-rate-medium"

        return "pass-rate-low"

    @staticmethod
    def _create_result_row(result: TestResult) -> str:
        status_class = {
            EvaluationStatus.PASS: "status-pass",
            EvaluationStatus.FAIL: "status-fail",
            EvaluationStatus.ERROR: "status-error",
        }.get(
            result.status,
            "status-error",
        )

        return f"""
    <tr>
        <td>{escape(str(result.test_id))}</td>
        
        <td>{escape(result.provider)}</td>
    
        <td>{escape(result.model)}</td>
    
        <td>
            <span class="status {status_class}">
                {escape(str(result.status.value))}
            </span>
        </td>
    
        <td class="numeric">
            {result.response_time_seconds:.3f} s
        </td>
        
        <td class="numeric">
             ${result.estimated_cost_usd:.6f}
        </td>
    
        <td>
            <details class="result-details">
                <summary>View details</summary>
    
                <div class="details-content">
                    <div class="detail-section">
                        <h3>Test Information</h3>
    
                        <dl class="detail-grid">
                        <dt>Provider</dt>
                            <dd>{escape(result.provider)}</dd>
                            
                            <dt>Model</dt>
                            <dd>{escape(result.model)}</dd>
                            
                            <dt>Estimated cost</dt>
                            <dd>${result.estimated_cost_usd:.6f}</dd>
                        <dt>Name</dt>
                            <dd>{escape(result.name)}</dd>
    
                            <dt>Category</dt>
                            <dd>{escape(result.category)}</dd>
    
                            <dt>Assertion</dt>
                            <dd>{escape(str(result.assertion_type.value))}</dd>
    
                            <dt>Expected</dt>
                            <dd>
                                <code>{escape(str(result.expected))}</code>
                            </dd>
                        </dl>
                    </div>
    
                    <div class="detail-section">
                        <h3>Prompt</h3>
    
                        <pre>{escape(result.prompt)}</pre>
                    </div>
    
                    <div class="detail-section">
                        <h3>Actual Response</h3>
    
                        <pre>{escape(result.actual_response)}</pre>
                    </div>
    
                    <div class="detail-section">
                        <h3>Evaluation Reason</h3>
    
                        <p>{escape(result.reason)}</p>
                    </div>
    
                    <div class="detail-section">
                        <h3>Performance Metrics</h3>
    
                        <dl class="detail-grid metrics-grid">
                            <dt>Prompt tokens</dt>
                            <dd>{result.prompt_tokens}</dd>
    
                            <dt>Output tokens</dt>
                            <dd>{result.output_tokens}</dd>
    
                            <dt>Prompt latency</dt>
                            <dd>
                                {result.prompt_latency_seconds:.3f} s
                            </dd>
    
                            <dt>Generation latency</dt>
                            <dd>
                                {result.generation_latency_seconds:.3f} s
                            </dd>
    
                            <dt>Model load time</dt>
                            <dd>
                                {result.model_load_seconds:.3f} s
                            </dd>
    
                            <dt>Prompt speed</dt>
                            <dd>
                                {result.prompt_tokens_per_second:.2f}
                                tok/s
                            </dd>
    
                            <dt>Generation speed</dt>
                            <dd>
                                {result.generation_tokens_per_second:.2f}
                                tok/s
                            </dd>
    
                            <dt>Total response time</dt>
                            <dd>
                                {result.response_time_seconds:.3f} s
                            </dd>
                        </dl>
                    </div>
                </div>
            </details>
        </td>
    </tr>
    """
