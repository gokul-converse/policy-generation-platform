import asyncio
import json

from app.agents.foundry.agent import get_ui_json_agent


async def main():
    agent = get_ui_json_agent()

    sample_policy = """
    Employee Annual Leave Policy
 
Purpose:
To outline the annual leave entitlement and procedure for employees, ensuring that all employees receive a fair and consistent 
amount of leave, while also ensuring that business needs are met.
 
Scope:
This policy applies to all employees of [Company Name].
 
1. Annual Leave Entitlement:
All employees are entitled to 25 days of annual leave per year, including public holidays.
 
2. Approval Process:
Before taking annual leave, employees must obtain approval from their manager. The approval process is as follows:
 
* The employee must submit a leave request to their manager at least two weeks in advance, providing the dates of leave.
* The manager will review the leave request and respond to the employee within two days, indicating whether the request is approved 
or not.
* If the request is approved, the employee will receive a confirmation email with the details of the leave.
 
3. Leave Period:
The annual leave period begins on the first day of the leave request and ends on the date indicated in the leave request.
 
4. Leave Entitlement Types:
The annual leave entitlement includes:
 
* Annual leave: 25 days per year
* Public holidays: included in the annual leave entitlement
 
5. Carry-Over and Accrual:
No carry-over or accrual of annual leave is allowed. If an employee takes annual leave for a longer period than they have accrued, 
they must make up the difference when they return to work.
 
6. Request for Leave:
Employees must submit a leave request to their manager at least two weeks in advance to ensure that business needs are met. 
Employees can also request leave for special circumstances, such as bereavement or medical leave, using the same process.
 
7. Leave Cancellation:
If an employee needs to cancel their leave request, they must notify their manager as soon as possible. The manager will assess the 
impact on the business and may adjust the leave schedule accordingly.
 
8. Return to Work:
After taking annual leave, employees are expected to return to work on the date indicated in the leave request. If an employee is 
unable to return to work on the scheduled date, they must notify their manager and make arrangements for coverage.
 
9. Consequences:
Failure to follow this policy may result in disciplinary action, up to and including termination.
 
10. Review and Revision:
This policy will be reviewed and revised annually, or as needed.
 
By following this policy, employees can ensure that they receive the annual leave entitlement they are entitled to, while also 
meeting the needs of the business.
    """

    result = await agent.run(sample_policy)

    print("\n=== GENERATED UI JSON ===")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
