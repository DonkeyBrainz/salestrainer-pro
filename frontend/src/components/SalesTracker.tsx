import React from 'react';
import { EvaluationState, SalesStage } from '@/types';
import { CheckCircle2, Circle, Trophy, Sparkles, Cloud, CloudOff, CloudCheck } from 'lucide-react';

interface SalesTrackerProps {
  evaluation: EvaluationState;
}

const SalesTracker: React.FC<SalesTrackerProps> = ({ evaluation }) => {
  const { currentStage, checklist, feedback, cloudSyncStatus } = evaluation;

  // Calculate Global Progress
  const categories = ['engage', 'ask', 'show', 'yes'] as const;
  let totalItems = 0;
  let completedItems = 0;

  categories.forEach(cat => {
    const items = Object.values(checklist[cat]);
    totalItems += items.length;
    completedItems += items.filter(Boolean).length;
  });

  const globalProgressPercentage = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0;

  // Helper to render a stage block
  const renderStage = (stageName: string, stageId: SalesStage, items: { label: string; completed: boolean }[]) => {
    const isActive = currentStage === stageId;

    // Calculate Stage Progress
    const stageTotal = items.length;
    const stageCompleted = items.filter(i => i.completed).length;
    const stagePercent = stageTotal > 0 ? Math.round((stageCompleted / stageTotal) * 100) : 0;

    return (
      <div className={`
        flex flex-col mb-4 p-4 rounded-xl border transition-all duration-500 relative overflow-hidden
        ${isActive
          ? 'bg-white border-[#8B5E3C] shadow-md scale-100 opacity-100'
          : 'bg-stone-50 border-stone-200 opacity-70 scale-95'
        }
      `}>
        <div className="flex items-center justify-between mb-2 z-10 relative">
          <h3 className={`font-serif-display font-semibold text-lg ${isActive ? 'text-[#8B5E3C]' : 'text-stone-400'}`}>
            {stageName}
          </h3>
          <div className="flex items-center gap-2">
             {isActive && <span className="text-[10px] bg-[#8B5E3C] text-white px-2 py-0.5 rounded-full uppercase tracking-widest animate-pulse">Active</span>}
             <span className={`text-xs font-mono ${isActive ? 'text-[#8B5E3C]' : 'text-stone-400'}`}>
               {stageCompleted}/{stageTotal}
             </span>
          </div>
        </div>

        {/* Stage Progress Bar */}
        <div className="w-full h-1 bg-stone-100 rounded-full mb-3 overflow-hidden">
             <div
                className={`h-full transition-all duration-700 ease-out ${isActive ? 'bg-[#8B5E3C]' : 'bg-stone-300'}`}
                style={{ width: `${stagePercent}%` }}
             />
        </div>

        <div className="space-y-2 z-10 relative">
          {items.map((item, idx) => (
            <div key={idx} className="flex items-start gap-2">
              {item.completed ? (
                <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0 mt-0.5 animate-bounce" />
              ) : (
                <Circle className="w-4 h-4 text-stone-300 shrink-0 mt-0.5" />
              )}
              <span className={`text-sm ${item.completed ? 'text-stone-800 font-medium' : 'text-stone-400'}`}>
                {item.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col w-full bg-white/50 border-r border-stone-200 p-4 overflow-y-auto">

      {/* HUD Header with Global Progress */}
      <div className="flex flex-col gap-2 mb-6">
        <div className="flex items-center justify-between opacity-80">
          <div className="flex items-center gap-2">
            <Trophy className="w-5 h-5 text-[#8B5E3C]" />
            <span className="text-xs uppercase tracking-[0.2em] font-bold text-stone-600">Performance HUD</span>
          </div>
          <div className="flex items-center gap-2">
             {/* Wrap icons in span with title attribute because Lucide components do not accept title directly as a prop */}
             {cloudSyncStatus === 'synced' ? (
                 <span title="Progress synced to GCS">
                   <CloudCheck className="w-4 h-4 text-green-500" />
                 </span>
             ) : cloudSyncStatus === 'syncing' ? (
                 <span title="Syncing to GCS...">
                   <Cloud className="w-4 h-4 text-blue-400 animate-pulse" />
                 </span>
             ) : cloudSyncStatus === 'error' ? (
                 <span title="GCS Sync Failed">
                   <CloudOff className="w-4 h-4 text-red-400" />
                 </span>
             ) : null}
             <span className="text-xs font-bold text-[#8B5E3C]">{globalProgressPercentage}%</span>
          </div>
        </div>

        {/* Global Progress Bar */}
        <div className="w-full h-1.5 bg-stone-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-[#8B5E3C] to-[#C4A484] transition-all duration-1000 ease-out rounded-full"
            style={{ width: `${globalProgressPercentage}%` }}
          />
        </div>
      </div>

      {/* Live Feedback Toast (In-HUD) */}
      {feedback && (
        <div className="mb-6 bg-gradient-to-r from-[#8B5E3C] to-[#724C31] text-white p-3 rounded-lg shadow-lg animate-fade-in-up">
           <div className="flex items-center gap-2 mb-1">
             <Sparkles className="w-3 h-3 text-yellow-200" />
             <span className="text-[9px] uppercase tracking-widest font-bold">Coach Says</span>
           </div>
           <p className="text-sm font-medium leading-tight">{feedback}</p>
        </div>
      )}

      {/* STAGE 1: ENGAGE */}
      {renderStage('1. Engage', 'ENGAGE', [
        { label: 'Non-Business Greet', completed: checklist.engage.nonBusinessGreet },
        { label: 'Build Rapport', completed: checklist.engage.establishedRapport },
        { label: 'Mention Manager', completed: checklist.engage.managerMention },
      ])}

      {/* STAGE 2: ASK */}
      {renderStage('2. Ask', 'ASK', [
        { label: 'Ask Critical Questions', completed: checklist.ask.criticalQuestions },
        { label: 'Layer 2 Discovery', completed: checklist.ask.layer2Discovery },
        { label: 'Identify PBMs', completed: checklist.ask.pbmsIdentified },
      ])}

      {/* STAGE 3: SHOW */}
      {renderStage('3. Show', 'SHOW', [
        { label: 'Power Demonstration', completed: checklist.show.powerDemo },
        { label: 'Feature -> Benefit -> PBM', completed: checklist.show.featureBenefitPbm },
        { label: 'Offer Protection Plan', completed: checklist.show.protectionPlan },
      ])}

      {/* STAGE 4: YES */}
      {renderStage('4. Yes', 'YES', [
        { label: 'Pay Your Way (Financing)', completed: checklist.yes.payYourWay },
        { label: 'Clear Constraints', completed: checklist.yes.clearConstraint },
        { label: 'Close the Sale', completed: checklist.yes.closedSale },
      ])}
    </div>
  );
};

export default SalesTracker;
