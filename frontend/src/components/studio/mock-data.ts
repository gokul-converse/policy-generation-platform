import { Skill, PolicySection, PolicyItem } from './types';

export const createSeedSkills = (): Skill[] => [
  {
    id: 's1',
    name: 'Annual leave accrual',
    rule: 'Staff accrue 1.5 days of paid leave per month after probation.',
    ver: 1,
  },
  {
    id: 's2',
    name: 'Manager approval',
    rule: 'Requests over three days need written approval from the line manager.',
    ver: 1,
  },
];

export const createInitialSections = (): PolicySection[] => [
  {
    sectionId: 'SEC-001',
    heading: 'ELIGIBILITY & SCOPE',
    paragraph: 'This policy applies to all permanent and contract staff who have successfully completed their probationary period.',
  },
  {
    sectionId: 'SEC-002',
    heading: 'ANNUAL LEAVE ACCRUAL',
    paragraph: 'Staff accrue 1.5 days of paid leave per month after probation. Accrual begins on the first day following completion of the probation period.',
    appliedSkillId: 's1',
  },
  {
    sectionId: 'SEC-003',
    heading: 'CARRY-OVER POLICY',
    paragraph: 'Unused annual leave may carry over up to a maximum of 5 days into the following calendar year. Any remaining unused leave beyond 5 days expires on December 31.',
  },
  {
    sectionId: 'SEC-004',
    heading: 'MANAGER APPROVAL & TIMELINES',
    paragraph: 'Requests over three days need written approval from the line manager. All applications must be submitted at least 5 working days in advance.',
    appliedSkillId: 's2',
  },
];

export const INITIAL_POLICIES: PolicyItem[] = [
  {
    id: 'p1',
    title: 'Remote work policy',
    state: 'Published',
    when: '12 Oct',
    skills: createSeedSkills(),
    sections: [
      {
        sectionId: 'SEC-R01',
        heading: 'ELIGIBILITY',
        paragraph: 'Full-time staff in good standing are eligible to request hybrid or full-time remote working arrangements with department head approval.',
      },
      {
        sectionId: 'SEC-R02',
        heading: 'EQUIPMENT & SECURITY',
        paragraph: 'All remote work must be conducted on company-managed devices adhering to standard cybersecurity and VPN policies.',
      },
    ],
  },
  {
    id: 'p2',
    title: 'Expense reimbursement',
    state: 'Draft',
    when: '3 Oct',
    skills: createSeedSkills(),
    sections: [
      {
        sectionId: 'SEC-E01',
        heading: 'ALLOWABLE EXPENSES',
        paragraph: 'Reimbursable expenses include legitimate business travel, client meals up to approved per diems, and necessary office supplies.',
      },
      {
        sectionId: 'SEC-E02',
        heading: 'SUBMISSION TIMELINE',
        paragraph: 'Itemized receipts must be submitted within 30 days of expense incurrence via the employee portal.',
      },
    ],
  },
];

export const REQUIREMENT_QUESTIONS = [
  'Which employee groups does it cover, and do they accrue leave differently?',
  'How many days a year, and can unused days carry over?',
  'Who approves requests, and how far ahead must staff apply?',
];

export const SUGGESTION_CHIPS = [
  'Employee leave policy',
  'Remote work policy',
  'Expense reimbursement',
];

export const STEP_NAMES = [
  '',
  'Requirements',
  'Skills',
  'Review policy',
  'Preview',
  'Master policy',
];
