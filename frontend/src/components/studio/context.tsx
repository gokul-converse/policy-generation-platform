'use client';

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
  Skill,
  PolicySection,
  PolicyItem,
  ChatMessage,
  ScreenNumber,
} from './types';
import {
  createSeedSkills,
  createInitialSections,
  INITIAL_POLICIES,
  REQUIREMENT_QUESTIONS,
} from './mock-data';

export const ROUTE_MAP: Record<ScreenNumber, string> = {
  1: '/',
  2: '/skills',
  3: '/policy-review',
  4: '/preview',
  5: '/master-policy',
};

export const PATH_TO_SCREEN: Record<string, ScreenNumber> = {
  '/': 1,
  '/skills': 2,
  '/policy-review': 3,
  '/preview': 4,
  '/master-policy': 5,
};

interface StudioContextValue {
  screen: ScreenNumber;
  stack: ScreenNumber[];
  sidebarOpen: boolean;
  requirementId: string;
  policies: PolicyItem[];
  currentPolicyId: string | null;
  // Screen 1 Chat
  messages: ChatMessage[];
  askedCount: number;
  isFinalized: boolean;
  isBusy: boolean;
  // Screen 2 & 3
  skills: Skill[];
  sections: PolicySection[];
  selectedSectionId: string | null;
  highlightedSkillId: string | null;
  isCreatingSkill: boolean;
  skillMenuOpen: boolean;
  // Screen 4
  previewTab: 'ui' | 'js';
  isPreviewLoading: boolean;
  // Drawer & Toast
  drawerSkillId: string | null;
  toastMessage: string | null;
  // Actions
  showToast: (msg: string) => void;
  simulateApi: (method: string, path: string, durationMs?: number) => Promise<void>;
  navigate: (screen: ScreenNumber) => void;
  goBack: () => void;
  goHome: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  handleNewPolicy: () => void;
  handleSendMessage: (text: string) => Promise<void>;
  handleContinueToSkills: () => void;
  handleCreateSkill: (ruleText: string) => Promise<void>;
  handleGeneratePolicy: () => Promise<void>;
  handleSelectSection: (sectionId: string | null) => void;
  handlePickSkillForSection: (skillId: string) => void;
  handleRegenerateSection: (instructions: string) => Promise<void>;
  handleFinalizeMasterPolicy: () => Promise<void>;
  setPreviewTab: (tab: 'ui' | 'js') => void;
  handleSaveAndGoToPolicies: () => Promise<void>;
  handleViewPolicy: (id: string) => void;
  handleEditPolicy: (id: string) => void;
  handlePreviewPolicy: (id: string) => void;
  openSkillDrawer: (skillId: string) => void;
  closeSkillDrawer: () => void;
}

const StudioContext = createContext<StudioContextValue | null>(null);

export const StudioProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname();

  // Derive screen number from current path (defaults to 1 if on root or playground)
  const screen: ScreenNumber = PATH_TO_SCREEN[pathname] || 1;

  const [stack, setStack] = useState<ScreenNumber[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [requirementId] = useState<string>('REQ-2041');
  const [policies, setPolicies] = useState<PolicyItem[]>(INITIAL_POLICIES);
  const [currentPolicyId, setCurrentPolicyId] = useState<string | null>(null);

  // Screen 1 Chat
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [askedCount, setAskedCount] = useState<number>(0);
  const [isFinalized, setIsFinalized] = useState<boolean>(false);
  const [isBusy, setIsBusy] = useState<boolean>(false);

  // Screen 2 & 3
  const [skills, setSkills] = useState<Skill[]>(createSeedSkills());
  const [sections, setSections] = useState<PolicySection[]>(createInitialSections());
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(null);
  const [highlightedSkillId, setHighlightedSkillId] = useState<string | null>(null);
  const [isCreatingSkill, setIsCreatingSkill] = useState<boolean>(false);
  const [skillMenuOpen, setSkillMenuOpen] = useState<boolean>(false);

  // Screen 4
  const [previewTab, setPreviewTab] = useState<'ui' | 'js'>('ui');
  const [isPreviewLoading, setIsPreviewLoading] = useState<boolean>(false);

  // Drawer & Toast
  const [drawerSkillId, setDrawerSkillId] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Hydrate from sessionStorage once on client mount (for resilience on refresh)
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem('policy_studio_session_state');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.messages) setMessages(parsed.messages);
        if (parsed.askedCount !== undefined) setAskedCount(parsed.askedCount);
        if (parsed.isFinalized !== undefined) setIsFinalized(parsed.isFinalized);
        if (parsed.skills?.length) setSkills(parsed.skills);
        if (parsed.sections?.length) setSections(parsed.sections);
        if (parsed.policies?.length) setPolicies(parsed.policies);
        if (parsed.currentPolicyId !== undefined) setCurrentPolicyId(parsed.currentPolicyId);
      }
    } catch {
      // Ignore sessionStorage errors
    }
  }, []);

  // Save to sessionStorage on state changes
  useEffect(() => {
    try {
      const stateToPersist = {
        messages,
        askedCount,
        isFinalized,
        skills,
        sections,
        policies,
        currentPolicyId,
      };
      sessionStorage.setItem('policy_studio_session_state', JSON.stringify(stateToPersist));
    } catch {
      // Ignore sessionStorage errors
    }
  }, [messages, askedCount, isFinalized, skills, sections, policies, currentPolicyId]);

  const showToast = useCallback((msg: string) => {
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    setToastMessage(msg);
    toastTimerRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 1600);
  }, []);

  const simulateApi = useCallback(
    async (method: string, path: string, durationMs: number = 700) => {
      showToast(`${method} ${path}`);
      await new Promise((r) => setTimeout(r, durationMs));
      showToast(`${method} ${path} · 200`);
    },
    [showToast]
  );

  const navigate = useCallback(
    (targetScreen: ScreenNumber) => {
      setStack((prev) => [...prev, screen]);
      if (typeof window !== 'undefined' && window.innerWidth <= 820) {
        setSidebarOpen(false);
      }
      const targetRoute = ROUTE_MAP[targetScreen] || ROUTE_MAP[1];
      router.push(targetRoute);
      if (typeof window !== 'undefined') window.scrollTo(0, 0);
    },
    [screen, router]
  );

  const goBack = useCallback(() => {
    setIsPreviewLoading(false);
    setSelectedSectionId(null);
    setSkillMenuOpen(false);
    router.back();
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
  }, [router]);

  const goHome = useCallback(() => {
    setStack([]);
    router.push(ROUTE_MAP[1]);
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
  }, [router]);

  const toggleSidebar = useCallback(() => {
    setSidebarOpen((prev) => !prev);
  }, []);

  const handleNewPolicy = useCallback(() => {
    setStack([]);
    setCurrentPolicyId(null);
    setMessages([]);
    setAskedCount(0);
    setIsFinalized(false);
    setSkills(createSeedSkills());
    setSections(createInitialSections());
    setSelectedSectionId(null);
    try {
      sessionStorage.removeItem('policy_studio_session_state');
    } catch {
      // Ignore
    }
    if (typeof window !== 'undefined' && window.innerWidth <= 820) {
      setSidebarOpen(false);
    }
    router.push(ROUTE_MAP[1]);
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
  }, [router]);

  // Screen 1: Send Message & deterministic question cycle
  const handleSendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isBusy) return;

      const userMsg: ChatMessage = {
        id: `u-${Date.now()}`,
        role: 'user',
        text: trimmed,
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsBusy(true);

      await simulateApi('WS', '/ws/requirements', 900);
      setIsBusy(false);

      if (askedCount < REQUIREMENT_QUESTIONS.length) {
        const nextQuestion = REQUIREMENT_QUESTIONS[askedCount];
        const agentMsg: ChatMessage = {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: nextQuestion,
        };
        setAskedCount((c) => c + 1);
        setMessages((prev) => [...prev, agentMsg]);
      } else {
        setIsFinalized(true);
        const draftMsg: ChatMessage = {
          id: `draft-${Date.now()}`,
          role: 'assistant',
          text: 'Employee leave policy draft',
          isDraft: true,
        };
        setMessages((prev) => [...prev, draftMsg]);
      }
    },
    [askedCount, isBusy, simulateApi]
  );

  const handleContinueToSkills = useCallback(() => {
    navigate(2);
  }, [navigate]);

  // Screen 2: Create Skill
  const handleCreateSkill = useCallback(
    async (ruleText: string) => {
      const trimmed = ruleText.trim();
      if (!trimmed) return;

      setIsCreatingSkill(true);
      await simulateApi('POST', '/api/skills', 1100);

      const words = trimmed.replace(/[.]/g, '').split(' ').slice(0, 3).join(' ');
      const skillName = words.charAt(0).toUpperCase() + words.slice(1);
      const newSkill: Skill = {
        id: `k${Date.now()}`,
        name: skillName,
        rule: trimmed,
        ver: 1,
      };

      setSkills((prev) => [newSkill, ...prev]);
      setIsCreatingSkill(false);
    },
    [simulateApi]
  );

  const handleGeneratePolicy = useCallback(async () => {
    await simulateApi('POST', '/api/policies/generate', 500);
    navigate(3);
  }, [navigate, simulateApi]);

  // Screen 3: Section Selection & Regeneration
  const handleSelectSection = useCallback((sectionId: string | null) => {
    setSelectedSectionId(sectionId);
    setSkillMenuOpen(false);
  }, []);

  const handlePickSkillForSection = useCallback(
    (skillId: string) => {
      if (!selectedSectionId) return;
      setSections((prev) =>
        prev.map((sec) =>
          sec.sectionId === selectedSectionId
            ? { ...sec, appliedSkillId: skillId }
            : sec
        )
      );
      setSkillMenuOpen(false);
    },
    [selectedSectionId]
  );

  const handleRegenerateSection = useCallback(
    async (instructions: string) => {
      if (!selectedSectionId || !instructions.trim()) return;

      const trimmedInst = instructions.trim();
      const currentSection = sections.find((s) => s.sectionId === selectedSectionId);
      const activeSkill = skills.find((s) => s.id === currentSection?.appliedSkillId) || skills[0];

      await simulateApi('PATCH', `/api/skills/${activeSkill?.id || 'section'}`, 800);

      if (activeSkill) {
        setSkills((prev) =>
          prev.map((k) =>
            k.id === activeSkill.id
              ? {
                  ...k,
                  rule: `${k.rule.replace(/\.$/, '')}. ${trimmedInst.charAt(0).toUpperCase() + trimmedInst.slice(1).replace(/\.$/, '')}.`,
                  ver: k.ver + 1,
                }
              : k
          )
        );
        setHighlightedSkillId(activeSkill.id);
        setTimeout(() => setHighlightedSkillId(null), 1800);
      }

      setSections((prev) =>
        prev.map((sec) => {
          if (sec.sectionId === selectedSectionId) {
            const updatedParagraph = `${sec.paragraph.replace(/\.$/, '')}. ${trimmedInst.charAt(0).toUpperCase() + trimmedInst.slice(1).replace(/\.$/, '')}.`;
            return {
              ...sec,
              paragraph: updatedParagraph,
            };
          }
          return sec;
        })
      );

      setSelectedSectionId(null);
    },
    [selectedSectionId, sections, skills, simulateApi]
  );

  const handleFinalizeMasterPolicy = useCallback(async () => {
    setPreviewTab('ui');
    setIsPreviewLoading(true);
    navigate(4);
    await simulateApi('POST', '/api/master-policy/render', 2000);
    setIsPreviewLoading(false);
  }, [navigate, simulateApi]);

  const handleSaveAndGoToPolicies = useCallback(async () => {
    await simulateApi('PUT', '/api/policies', 500);
    if (!currentPolicyId) {
      const newPolicy: PolicyItem = {
        id: `p${Date.now()}`,
        title: 'Employee leave policy',
        state: 'Draft',
        when: 'Today',
        skills: [...skills],
        sections: [...sections],
      };
      setPolicies((prev) => [newPolicy, ...prev]);
    }
    setCurrentPolicyId(null);
    setStack([]);
    setMessages([]);
    setAskedCount(0);
    setIsFinalized(false);
    setSkills(createSeedSkills());
    setSections(createInitialSections());
    router.push(ROUTE_MAP[1]);
    if (typeof window !== 'undefined') window.scrollTo(0, 0);
  }, [currentPolicyId, skills, sections, simulateApi, router]);

  const handleViewPolicy = useCallback(
    (id: string) => {
      const target = policies.find((p) => p.id === id);
      if (target) {
        setCurrentPolicyId(target.id);
        setSkills(target.skills.map((k) => ({ ...k })));
        setSections(target.sections?.length ? target.sections.map((s) => ({ ...s })) : createInitialSections());
        navigate(5);
      }
    },
    [policies, navigate]
  );

  const handleEditPolicy = useCallback(
    (id: string) => {
      const target = policies.find((p) => p.id === id);
      if (target) {
        setCurrentPolicyId(target.id);
        setSkills(target.skills.map((k) => ({ ...k })));
        setSections(target.sections?.length ? target.sections.map((s) => ({ ...s })) : createInitialSections());
      }
      navigate(3);
    },
    [policies, navigate]
  );

  const handlePreviewPolicy = useCallback(
    (id: string) => {
      const target = policies.find((p) => p.id === id);
      if (target) {
        setCurrentPolicyId(target.id);
        setSkills(target.skills.map((k) => ({ ...k })));
        setSections(target.sections?.length ? target.sections.map((s) => ({ ...s })) : createInitialSections());
      }
      setIsPreviewLoading(false);
      setPreviewTab('ui');
      navigate(4);
    },
    [policies, navigate]
  );

  const openSkillDrawer = useCallback((skillId: string) => {
    setDrawerSkillId(skillId);
  }, []);

  const closeSkillDrawer = useCallback(() => {
    setDrawerSkillId(null);
  }, []);

  return (
    <StudioContext.Provider
      value={{
        screen,
        stack,
        sidebarOpen,
        requirementId,
        policies,
        currentPolicyId,
        messages,
        askedCount,
        isFinalized,
        isBusy,
        skills,
        sections,
        selectedSectionId,
        highlightedSkillId,
        isCreatingSkill,
        skillMenuOpen,
        previewTab,
        isPreviewLoading,
        drawerSkillId,
        toastMessage,
        showToast,
        simulateApi,
        navigate,
        goBack,
        goHome,
        toggleSidebar,
        setSidebarOpen,
        handleNewPolicy,
        handleSendMessage,
        handleContinueToSkills,
        handleCreateSkill,
        handleGeneratePolicy,
        handleSelectSection,
        handlePickSkillForSection,
        handleRegenerateSection,
        handleFinalizeMasterPolicy,
        setPreviewTab,
        handleSaveAndGoToPolicies,
        handleViewPolicy,
        handleEditPolicy,
        handlePreviewPolicy,
        openSkillDrawer,
        closeSkillDrawer,
      }}
    >
      {children}
    </StudioContext.Provider>
  );
};

export const useStudio = (): StudioContextValue => {
  const context = useContext(StudioContext);
  if (!context) {
    throw new Error('useStudio must be used within a StudioProvider');
  }
  return context;
};
