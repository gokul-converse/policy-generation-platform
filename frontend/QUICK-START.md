# Quick Start Guide - Policy Generator UI

## Get Running in 2 Minutes

### 1. Install Dependencies
```bash
cd frontend
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

### 3. Open Browser
Navigate to `http://localhost:3000`

That's it! The app is running with mock data.

---

## Try It Out

### Basic Workflow
1. **Enter a policy description**: "Remote work policy for software developers"
2. **Wait 2 seconds** - Policy generates with 8 paragraphs
3. **Hover over any paragraph** - See edit icon
4. **Click edit icon** - Inline form appears
5. **Enter instruction**: "Make this more concise"
6. **Click Regenerate** - Watch that paragraph update (1.5s)
7. **Click "Generate UI"** - Wait 3 seconds
8. **Full-screen preview** - See your dashboard
9. **Click "Show JSON"** - See the component structure
10. **Click "Regenerate UI"** - Try customizing the UI

---

## Key Files to Know

### Main Application
- `src/app/page.tsx` - Main page with state management

### Components
- `src/components/features/policy-description-form.tsx` - Step 1
- `src/components/features/policy-review.tsx` - Steps 2 & 3
- `src/components/features/ui-preview.tsx` - Step 4

### Services
- `src/services/policy.service.ts` - **API integration layer**
- `src/services/mock-policy.service.ts` - Mock implementations

### Types
- `src/types/policy.ts` - All domain types

---

## Customize Mock Data

### Change Mock Delays
```typescript
// src/services/mock-policy.service.ts

const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// In generatePolicy:
await delay(2000);  // Change this number (milliseconds)
```

### Change Generated Paragraphs
```typescript
// src/services/mock-policy.service.ts

const generateMockParagraphs = (description: string): Paragraph[] => {
  const topics = [
    'Purpose and Scope',
    'Your Custom Topic',  // Add/modify topics here
    // ...
  ];
  // ...
}
```

### Change UI Components
```typescript
// src/services/mock-policy.service.ts

const generateMockUIComponents = (policy: Policy, instructions?: string): UIComponent[] => {
  // Add/modify components in this array
  const components: UIComponent[] = [
    {
      type: 'header',
      props: { /* ... */ },
    },
    // Add your custom components here
  ];
}
```

---

## Connect to Backend

### Method 1: Feature Flag (Easiest)
```typescript
// src/services/policy.service.ts

const USE_MOCK_API = false;  // Change true to false
```

### Method 2: Environment Variable
```bash
# Create .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Then update service:
```typescript
// src/services/policy.service.ts
const USE_MOCK_API = process.env.NODE_ENV === 'development' ? false : true;
```

### Backend Endpoints Expected
- `POST /api/policy/generate`
  - Body: `{ description: string }`
  - Response: `{ policy: Policy }`

- `POST /api/policy/paragraph/regenerate`
  - Body: `{ paragraphId: string, instructions: string }`
  - Response: `{ paragraph: Paragraph }`

- `POST /api/policy/ui/generate`
  - Body: `{ policyId: string, instructions?: string }`
  - Response: `{ ui: GeneratedUI }`

---

## Common Tasks

### Add a New UI Component Type
1. Add type to `UIComponent` types in `src/types/policy.ts`
2. Add renderer in `src/components/features/ui-renderer.tsx`:
```typescript
case 'your-component':
  return <YourComponent {...component.props} />;
```
3. Add mock generator in `src/services/mock-policy.service.ts`

### Add Loading State
```typescript
const [isLoading, setIsLoading] = useState(false);

const handleAction = async () => {
  setIsLoading(true);
  try {
    await someAsyncAction();
  } finally {
    setIsLoading(false);
  }
};

<Button loading={isLoading} />
```

### Add Error Handling
```typescript
const [error, setError] = useState<string | null>(null);

try {
  await someAction();
  setError(null);  // Clear previous errors
} catch (err) {
  setError(err instanceof Error ? err.message : 'Unknown error');
}

{error && <div className="text-red-600">{error}</div>}
```

---

## Build for Production

### Development Build
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm start
```

### Build Output
- `.next/` folder contains optimized build
- Served on port 3000 by default

---

## Project Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm start        # Start production server
npm run lint     # Run ESLint
```

---

## Troubleshooting

### Port 3000 Already in Use
```bash
# Windows
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Use different port
npm run dev -- -p 3001
```

### Build Fails
```bash
# Clear cache and reinstall
rm -rf .next node_modules
npm install
npm run build
```

### TypeScript Errors
```bash
# Check types
npx tsc --noEmit
```

### Module Not Found
```bash
# Reinstall dependencies
npm ci
```

---

## File Structure Quick Reference

```
src/
├── app/
│   └── page.tsx           ← Main application
├── components/
│   ├── ui/                ← Reusable primitives
│   └── features/          ← Feature components
├── services/
│   ├── policy.service.ts  ← API layer (MODIFY FOR BACKEND)
│   └── mock-*.service.ts  ← Mock implementations
├── types/
│   └── policy.ts          ← Domain types
└── lib/
    └── utils.ts           ← Utilities
```

---

## Next Steps

1. **Explore the code** - Start with `src/app/page.tsx`
2. **Read the docs** - See `PHASE1-README.md` for detailed features
3. **Try the demo** - Follow `DEMO-GUIDE.md` for test scenarios
4. **Connect backend** - Update `policy.service.ts` feature flag
5. **Build features** - Add new components and services

---

## Getting Help

### Documentation
- `PHASE1-README.md` - Feature overview
- `ARCHITECTURE.md` - Technical details
- `DEMO-GUIDE.md` - Testing guide

### Code Comments
All files have inline documentation explaining:
- Component purpose
- Props interfaces
- State management
- Integration points

### Key Concepts
- **Mock API**: Simulated backend in `mock-policy.service.ts`
- **Real API**: Integration layer in `policy.service.ts`
- **Feature Flag**: `USE_MOCK_API` toggle
- **Types**: All in `src/types/`

---

**Ready to Code!** 🚀

The app is now running with full mock data. Start exploring and building!
