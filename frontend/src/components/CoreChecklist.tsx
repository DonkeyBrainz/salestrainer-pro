import React, { useMemo } from 'react';
import { SalesStage } from '@/types';
import { AT } from '@/styles/tokens';

interface CoreChecklistProps {
  currentStage: SalesStage;
  completedItems: string[];
  className?: string;
}

const STAGE_CONFIGS = [
  {
    name: 'CONNECT' as SalesStage,
    letter: 'C',
    title: 'Connect',
    items: ['warm_greeting', 'establish_credibility', 'create_comfort'],
  },
  {
    name: 'OBSERVE' as SalesStage,
    letter: 'O',
    title: 'Observe',
    items: ['needs_discovery', 'goal_identification', 'motivator_mapping'],
  },
  {
    name: 'RECOMMEND' as SalesStage,
    letter: 'R',
    title: 'Recommend',
    items: ['solution_presentation', 'value_connection', 'risk_mitigation'],
  },
  {
    name: 'EXECUTE' as SalesStage,
    letter: 'E',
    title: 'Execute',
    items: ['commitment_request', 'objection_handling', 'finalize_agreement'],
  },
];

const STAGE_ORDER: SalesStage[] = ['CONNECT', 'OBSERVE', 'RECOMMEND', 'EXECUTE'];

const CoreChecklist: React.FC<CoreChecklistProps> = ({ currentStage, completedItems }) => {
  const stageStats = useMemo(() => {
    return STAGE_CONFIGS.map(stage => {
      const completed = stage.items.filter(id => completedItems.includes(id)).length;
      return { name: stage.name, completed, total: stage.items.length };
    });
  }, [completedItems]);

  const currentIdx = STAGE_ORDER.indexOf(currentStage);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(4, 1fr)',
      gap: 0,
      borderBottom: `1px solid ${AT.hair}`,
      background: AT.bg,
    }}>
      {STAGE_CONFIGS.map((stage, i) => {
        const stats = stageStats[i];
        const isActive = stage.name === currentStage;
        const isDone = currentIdx > i;
        const isPending = currentIdx < i;
        const pct = stats.total > 0 ? (stats.completed / stats.total) * 100 : 0;

        return (
          <div
            key={stage.name}
            style={{
              padding: '12px 14px',
              borderBottom: isActive ? `2px solid ${AT.terra}` : '2px solid transparent',
              borderRight: i < 3 ? `1px solid ${AT.hair}` : 'none',
              opacity: isPending ? 0.45 : 1,
              transition: 'opacity 0.2s',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 26, height: 26, borderRadius: 6,
                background: isActive ? AT.terra : isDone ? AT.sage + '22' : AT.surface2,
                color: isActive ? AT.bg : isDone ? AT.sage : AT.inkSoft,
                fontFamily: AT.display, fontSize: 13, fontWeight: 700,
                display: 'grid', placeItems: 'center',
                transition: 'background 0.2s, color 0.2s',
              }}>
                {stage.letter}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontFamily: AT.mono, fontSize: 10.5,
                  letterSpacing: '0.16em',
                  color: isActive ? AT.ink : AT.inkSoft,
                  textTransform: 'uppercase',
                }}>
                  {stage.title}
                </div>
                <div style={{ height: 3, background: AT.hair, borderRadius: 2, marginTop: 5, overflow: 'hidden' }}>
                  <div style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: isDone ? AT.sage : AT.terra,
                    transition: 'width 0.3s ease-out',
                  }} />
                </div>
              </div>
              <div style={{ fontFamily: AT.mono, fontSize: 10, color: AT.inkMuted, letterSpacing: '0.1em' }}>
                {stats.completed}/{stats.total}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default CoreChecklist;
