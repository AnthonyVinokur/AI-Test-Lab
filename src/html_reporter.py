import datetime
from datetime import datetime
from html import escape
from pathlib import Path

from src.models import EvaluationStatus, TestResult


class HtmlReporter:
    """Writes AI test results to a styled HTML report."""

    def __init__(self, report_path: Path) -> None:
        self.report_path = report_path

    def write(self, results: list[TestResult]) -> None:
        self.report_path.parent.mkdir(parents=True, exist_ok=True)

        generated_at = datetime.now().astimezone().strftime(
            "%B %d, %Y at %I:%M:%S %p %Z"
        )
        model_name = results[0].model if results else "Unknown"

        passed = sum(
            result.status == EvaluationStatus.PASS
            for result in results
        )
        failed = sum(
            result.status == EvaluationStatus.FAIL
            for result in results
        )
        errors = len(results) - passed - failed

        result_rows = "\n".join(
            self._create_result_row(result)
            for result in results
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
        body {{
            margin: 0;
            padding: 32px;
            background-color: #f4f6f8;
            color: #1f2937;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        h1 {{
            margin-bottom: 8px;
        }}

        .subtitle {{
            margin-top: 0;
            color: #8e958c;
            font-size: 17px;
        }}
        
        .generated-at {{
            margin-top: 6px;
            margin-bottom: 28px;
            color: #64748b;
            font-size: 14px;
        }}

        .summary {{
            display: grid;
            grid-template-columns: repeat(4, minmax(120px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }}

        .summary-card {{
            padding: 18px;
            background-color: white;
            border-radius: 8px;
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

        .passed-value {{
            color: #15803d;
        }}

        .failed-value {{
            color: #b91c1c;
        }}

        .error-value {{
            color: #c2410c;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }}

        th,
        td {{
            padding: 14px;
            border-bottom: 1px solid #e5e7eb;
            text-align: left;
        }}

        th {{
            background-color: #1f2937;
            color: white;
        }}

        tr:hover {{
            background-color: #f9fafb;
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

        @media (max-width: 700px) {{
            body {{
                padding: 16px;
            }}

            .summary {{
                grid-template-columns: repeat(2, 1fr);
            }}

            table {{
                display: block;
                overflow-x: auto;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <h1>AI Test Lab Report</h1>
        
            <p class="subtitle"
            style="color: #8e958c:font-weight: bold:">
            Automated LLM evaluation results</p>
            <p <strong>Generated :</strong> </p>
            <p> {escape(generated_at)}</p>
            <p> Model: </p>
            <p><i>{escape(model_name)}</i></p> 
      

        <section class="summary">
            <div class="summary-card">
                <span class="summary-label">Total</span>
                <span class="summary-value">{len(results)}</span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Passed</span>
                <span class="summary-value passed-value">{passed}</span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Failed</span>
                <span class="summary-value failed-value">{failed}</span>
            </div>

            <div class="summary-card">
                <span class="summary-label">Errors</span>
                <span class="summary-value error-value">{errors}</span>
            </div>
        </section>

        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Status</th>
                    <th>Response Time</th>
                </tr>
            </thead>

            <tbody>
                {result_rows}
            </tbody>
        </table>
    </main>
</body>
<tr>

</html>
"""

        self.report_path.write_text(
            html_content,
            encoding="utf-8",
        )

    @staticmethod
    def _create_result_row(result: TestResult) -> str:
        status_class = {
            EvaluationStatus.PASS: "status-pass",
            EvaluationStatus.FAIL: "status-fail",
            EvaluationStatus.ERROR: "status-error",
        }.get(result.status, "status-error")

        return f"""
<tr>
    <td>{escape(str(result.test_id))}</td>
    <td>
        <span class="status {status_class}">
            {escape(str(result.status.value))}
        </span>
    </td>
    <td>{result.response_time_seconds:.3f} s</td>
    
</tr>


 
"""
