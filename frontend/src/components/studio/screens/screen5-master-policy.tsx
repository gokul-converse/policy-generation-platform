'use client';

import React from 'react';
import { useStudio } from '../context';

export const Screen5MasterPolicy: React.FC = () => {
  const { policies, currentPolicyId, skills } = useStudio();
  const currentPolicy = policies.find((p) => p.id === currentPolicyId) || {
    title: 'Employee leave policy',
  };

  return (
    <div className="view">
      <div className="card doc">
        <h2>{currentPolicy.title}</h2>
        <span className="mono" style={{ color: 'var(--mu)' }}>
          Master policy
        </span>

        {skills.map((k) => (
          <div key={k.id}>
            <h5>{k.name.toUpperCase()}</h5>
            <p>
              {k.rule} This applies to all covered employees.
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};
