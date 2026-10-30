export interface Skill {
  id: string;
  name: string;
  rule: string;
  ver: number;
}

export interface PolicySection {
  sectionId: string;
  heading: string;
  paragraph: string;
  appliedSkillId?: string;
}

export interface PolicyItem {
  id: string;
  title: string;
  state: 'Published' | 'Draft';
  when: string;
  skills: Skill[];
  sections: PolicySection[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  text: string;
  isDraft?: boolean;
}

export type ScreenNumber = 1 | 2 | 3 | 4 | 5;

export interface StudioState {
  screen: ScreenNumber;
  stack: ScreenNumber[];
  sidebarOpen: boolean;
  requirementId: string;
  policies: PolicyItem[];
  currentPolicyId: string | null;
  // Screen 1 Chat State
  messages: ChatMessage[];
  askedCount: number;
  isFinalized: boolean;
  isBusy: boolean;
  // Screen 2 & 3 Skills & Sections
  skills: Skill[];
  sections: PolicySection[];
  selectedSectionId: string | null;
  highlightedSkillId: string | null;
  isCreatingSkill: boolean;
  skillMenuOpen: boolean;
  // Screen 4 Preview State
  previewTab: 'ui' | 'js';
  isPreviewLoading: boolean;
  // Drawer & Toast
  drawerSkillId: string | null;
  toast: string | null;
}
