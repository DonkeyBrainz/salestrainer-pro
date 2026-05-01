import React, { useState, useMemo } from 'react';
import { CheckCircle2, Circle, ChevronDown, ChevronRight } from 'lucide-react';
import { SalesStage } from '@/types';

interface CoreChecklistProps {
  currentStage: SalesStage;
  completedItems: string[];
  className?: string;
}

interface ChecklistItem {
  id: string;
  label: string;
}

interface StageConfig {
  name: SalesStage;
  title: string;
  items: ChecklistItem[];
}

const STAGE_CONFIGS: StageConfig[] = [
  {
    name: 'ENGAGE',
    title: 'Engage',
    items: [
      { id: 'non_business_greet', label: 'Non-Business Greeting' },
      { id: 'established_rapport', label: 'Build Rapport' },
      { id: 'manager_mention', label: 'Manager Mention' },
    ],
  },
  {
    name: 'ASK',
    title: 'Ask',
    items: [
      { id: 'critical_questions', label: 'Critical Questions' },
      { id: 'layer2_discovery', label: 'Layer 2 Discovery' },
      { id: 'pbms_identified', label: 'PBMs Identified' },
    ],
  },
  {
    name: 'SHOW',
    title: 'Show',
    items: [
      { id: 'power_demo', label: 'Power Demo' },
      { id: 'feature_benefit_pbm', label: 'Feature-Benefit-PBM' },
      { id: 'protection_plan', label: 'Protection Plan' },
    ],
  },
  {
    name: 'YES',
    title: 'Yes',
    items: [
      { id: 'pay_your_way', label: 'Pay Your Way' },
      { id: 'clear_constraint', label: 'Clear Constraint' },
      { id: 'closed_sale', label: 'Closed Sale' },
    ],
  },
];

const CoreChecklist: React.FC<CoreChecklistProps> = ({
  currentStage,
  completedItems,
  className = '',
}) => {
  // Track which stages are expanded (current stage expanded by default)
  const [expandedStages, setExpandedStages] = useState<Set<SalesStage>>(
    new Set([currentStage])
  );

  // Update expanded stages when currentStage changes
  React.useEffect(() => {
    setExpandedStages((prev) => new Set([...prev, currentStage]));
  }, [currentStage]);

  const toggleStage = (stageName: SalesStage) => {
    setExpandedStages((prev) => {
      const next = new Set(prev);
      if (next.has(stageName)) {
        next.delete(stageName);
      } else {
        next.add(stageName);
      }
      return next;
    });
  };

  // Calculate stage completion stats
  const stageStats = useMemo(() => {
    return STAGE_CONFIGS.map((stage) => {
      const totalItems = stage.items.length;
      const completedCount = stage.items.filter((item) =>
        completedItems.includes(item.id)
      ).length;
      return {
        name: stage.name,
        completedCount,
        totalItems,
        isComplete: completedCount === totalItems,
      };
    });
  }, [completedItems]);

  return (
    <div
      className={`bg-gray-900 border border-gray-700 rounded-lg shadow-lg overflow-hidden ${className}`}
    >
      {/* Header */}
      <div className="px-4 py-3 bg-gray-800 border-b border-gray-700">
        <h3 className="text-sm font-bold uppercase tracking-wider text-gray-100">
          C.O.R.E. Selling System
        </h3>
      </div>

      {/* Stages List */}
      <div className="divide-y divide-gray-700">
        {STAGE_CONFIGS.map((stage, stageIndex) => {
          const isExpanded = expandedStages.has(stage.name);
          const isCurrent = currentStage === stage.name;
          const stats = stageStats[stageIndex];

          return (
            <div key={stage.name} className="group">
              {/* Stage Header - Clickable */}
              <button
                onClick={() => toggleStage(stage.name)}
                className={`
                  w-full px-4 py-3 flex items-center justify-between
                  transition-colors hover:bg-gray-800
                  ${isCurrent ? 'bg-gray-800' : 'bg-gray-900'}
                `}
              >
                <div className="flex items-center gap-3">
                  {/* Expand/Collapse Icon */}
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-400" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-400" />
                  )}

                  {/* Stage Title */}
                  <span
                    className={`
                      text-sm font-bold uppercase tracking-wider
                      ${isCurrent ? 'text-emerald-400' : 'text-gray-300'}
                    `}
                  >
                    {stage.title}
                  </span>
                </div>

                {/* Progress Badge */}
                <div
                  className={`
                    flex items-center gap-2 text-xs font-bold
                    ${
                      stats.isComplete
                        ? 'text-emerald-400'
                        : isCurrent
                        ? 'text-amber-400'
                        : 'text-gray-500'
                    }
                  `}
                >
                  <span>
                    {stats.completedCount}/{stats.totalItems}
                  </span>
                  {stats.isComplete && (
                    <CheckCircle2 className="w-4 h-4" />
                  )}
                </div>
              </button>

              {/* Checklist Items - Collapsible */}
              {isExpanded && (
                <div className="px-4 py-2 bg-gray-900/50 space-y-2">
                  {stage.items.map((item) => {
                    const isCompleted = completedItems.includes(item.id);

                    return (
                      <div
                        key={item.id}
                        className="flex items-start gap-3 px-2 py-1.5"
                      >
                        {/* Checkbox Icon */}
                        {isCompleted ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                        ) : (
                          <Circle className="w-4 h-4 text-gray-600 flex-shrink-0 mt-0.5" />
                        )}

                        {/* Item Label */}
                        <span
                          className={`
                            text-sm leading-snug
                            ${
                              isCompleted
                                ? 'text-gray-400 line-through'
                                : 'text-gray-300'
                            }
                          `}
                        >
                          {item.label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default CoreChecklist;
