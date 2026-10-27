import asyncio
import json

from app.agents.foundry.agent import get_ui_json_agent


async def main():
    agent = get_ui_json_agent()

    sample_policy = """
    ENTERPRISE POLICY: ENTERPRISE POLICY
Domain: hr | Version: 1 | Status: DRAFT
================================================================================
 
## Executive Summary
Employees receive 20 days of annual leave per year, and leave requests must be submitted at least 5 days before the leave starts.
 
## Table of Contents
1. Purpose and Scope
2. Definitions and Applicability
3. Core Policy Rules
4. Responsibilities and Administration
5. Compliance, Violations, and Review
 
--------------------------------------------------------------------------------
Section 1: Purpose and Scope [purpose]
--------------------------------------------------------------------------------
Purpose: This policy establishes the annual leave entitlement and the required notice for leave requests. It applies to all employees under the HR policy framework and supports effective workforce planning and consistent leave administration. This policy implements the validated requirements REQ-DEMO-001 and REQ-DEMO-002 as follows: REQ-DEMO-001 – Employees receive 20 days of annual leave per year. REQ-DEMO-002 – Leave requests must be submitted at least 5 days before the leave starts.
 
Traceable Requirements: REQ-DEMO-001, REQ-DEMO-002
 
--------------------------------------------------------------------------------
Section 2: Definitions and Applicability [definitions]
--------------------------------------------------------------------------------
Definitions and applicability: Annual Leave Entitlement means the paid time off allocated to an employee for annual leave, amounting to 20 days per year. Leave Start means the first day of the requested leave period. Notice Period means the minimum lead time required to submit a leave request, which is 5 days prior to the desired start date. This policy applies to all employees as defined in the HR policy framework. This section explicitly states applicability of the verified requirements REQ-DEMO-001 and REQ-DEMO-002.
 
Traceable Requirements: REQ-DEMO-001, REQ-DEMO-002
 
--------------------------------------------------------------------------------
Section 3: Core Policy Rules [rules]
--------------------------------------------------------------------------------
1. Annual Leave Entitlement: Each eligible employee is entitled to 20 days of annual leave per year. This entitlement is defined by REQ-DEMO-001. 2. Leave Request Notice: Leave requests must be submitted at least 5 days before the leave starts. This requirement is defined by REQ-DEMO-002.
 
Traceable Requirements: REQ-DEMO-001, REQ-DEMO-002
 
--------------------------------------------------------------------------------
Section 4: Responsibilities and Administration [roles]
--------------------------------------------------------------------------------
HR / People Operations: Maintain accurate records of leave balances and entitlement; process leave requests in accordance with this policy. Managers and Supervisors: Review and approve leave requests in a timely manner and ensure notice requirements are observed. Employees: Submit leave requests with at least 5 days’ notice before the intended start date in accordance with the notice period.
 
Traceable Requirements: REQ-DEMO-001, REQ-DEMO-002
 
--------------------------------------------------------------------------------
Section 5: Compliance, Violations, and Review [compliance]
--------------------------------------------------------------------------------
Compliance and enforcement: Non-compliance with entitlement or notice requirements may be addressed through standard internal disciplinary procedures as defined by company policy. Review and updates: This policy will be reviewed annually by HR and updated as needed.
 
Traceable Requirements: REQ-DEMO-001, REQ-DEMO-002
 
================================================================================
END OF POLICY DOCUMENT
================================================================================
    """

    result = await agent.run(sample_policy)

    print("\n=== GENERATED UI JSON ===")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
