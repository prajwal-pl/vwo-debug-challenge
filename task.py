## Importing libraries and files
from crewai import Task

from agents import financial_analyst, verifier
from tools import search_tool, read_data_tool

## Creating a task to help solve user's query
analyze_financial_document = Task(
    description="Analyze the financial document located at '{file_path}' to answer the user's query: {query}.\n\
Read the uploaded financial document carefully using the Read Financial Document tool with the path '{file_path}'.\n\
Provide a detailed analysis covering revenue, expenses, profit margins, cash flow, and key ratios.\n\
Identify notable trends, year-over-year changes, and significant financial events.\n\
Search the internet for relevant market context and recent news about the company.",

    expected_output="""A comprehensive financial analysis report including:
- Executive summary of key findings
- Revenue and profitability analysis with specific numbers from the document
- Key financial ratios (P/E, debt-to-equity, current ratio, ROE, etc.)
- Year-over-year trends and notable changes
- Market context from recent news and industry analysis
- Clear, data-driven conclusions that directly address the user's query""",

    agent=financial_analyst,
    tools=[read_data_tool],
    async_execution=False,
)

## Creating an investment analysis task
investment_analysis = Task(
    description="Based on the financial document analysis, provide investment recommendations for the query: {query}.\n\
The financial document is located at '{file_path}'. Use the Read Financial Document tool with this path if needed.\n\
Assess valuation metrics and compare with industry peers.\n\
Provide balanced buy/hold/sell recommendations supported by data from the document.\n\
Consider both short-term catalysts and long-term fundamentals.",

    expected_output="""A structured investment analysis including:
- Investment thesis with bull and bear cases
- Valuation analysis with relevant metrics
- Comparison with industry peers and benchmarks
- Specific, data-backed investment recommendations
- Key catalysts and risks to watch
- Appropriate disclaimers that this is not personalized financial advice""",

    agent=financial_analyst,
    tools=[read_data_tool],
    async_execution=False,
)

## Creating a risk assessment task
risk_assessment = Task(
    description="Perform a comprehensive risk assessment based on the financial document at '{file_path}' for the query: {query}.\n\
Evaluate market risk, credit risk, liquidity risk, and operational risk.\n\
Analyze debt levels, cash flow stability, and exposure to market volatility.\n\
Assess regulatory and compliance risks relevant to the company.\n\
Provide actionable risk mitigation recommendations.",

    expected_output="""A detailed risk assessment report including:
- Risk summary with severity ratings (low/medium/high)
- Market risk analysis (interest rate, currency, equity exposure)
- Credit and liquidity risk evaluation
- Operational and regulatory risk factors
- Stress test scenarios and their potential impact
- Recommended risk mitigation strategies (diversification, hedging, etc.)""",

    agent=financial_analyst,
    tools=[read_data_tool],
    async_execution=False,
)

    
verification = Task(
    description="Verify whether the uploaded document at '{file_path}' is a valid financial document.\n\
Use the Read Financial Document tool with the path '{file_path}' to read the document.\n\
Validate that the extracted data is consistent and complete.",

    expected_output="""A verification report including:
- Document type classification (10-K, 10-Q, earnings report, annual report, etc.)
- Confidence level in the classification
- Key financial sections identified in the document
- Any data quality issues or missing information flagged
- Confirmation of whether the document is suitable for financial analysis""",

    agent=financial_analyst,
    tools=[read_data_tool],
    async_execution=False
)