import React, { useEffect, useState } from 'react';
import { Persona, Difficulty } from '@/types';
import { fetchPersonas } from '@/services/personaService';
import { Loader2, AlertCircle, ChevronRight } from 'lucide-react';

interface PersonaSelectorProps {
  onSelect: (persona: Persona) => void;
  onCancel: () => void;
}

const DIFFICULTY_COLORS: Record<Difficulty, { bg: string; text: string; label: string }> = {
  high_regard: { bg: 'bg-emerald-50', text: 'text-emerald-600', label: 'High Regard' },
  medium_regard: { bg: 'bg-amber-50', text: 'text-amber-600', label: 'Medium Regard' },
  low_regard: { bg: 'bg-red-50', text: 'text-red-600', label: 'Low Regard' },
  no_regard: { bg: 'bg-stone-50', text: 'text-stone-600', label: 'No Regard' },
};

const PersonaSelector: React.FC<PersonaSelectorProps> = ({ onSelect, onCancel }) => {
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadPersonas = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchPersonas();
        setPersonas(data);
      } catch (err) {
        setError('Failed to load guest scenarios');
      } finally {
        setIsLoading(false);
      }
    };

    loadPersonas();
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-[#8B5E3C] animate-spin mx-auto mb-4" />
          <p className="text-stone-500">Loading scenarios...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center px-6">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-xl font-serif-display text-[#2C2825] mb-3">
            Unable to Load Scenarios
          </h3>
          <p className="text-stone-500 mb-6">{error}</p>
          <button
            onClick={onCancel}
            className="px-6 py-2 bg-stone-200 hover:bg-stone-300 rounded-full text-sm font-bold uppercase tracking-wider text-stone-600 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  // Group personas by difficulty
  const groupedPersonas = {
    high_regard: personas.filter((p) => p.difficulty === 'high_regard'),
    medium_regard: personas.filter((p) => p.difficulty === 'medium_regard'),
    low_regard: personas.filter((p) => p.difficulty === 'low_regard'),
    no_regard: personas.filter((p) => p.difficulty === 'no_regard'),
  };

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h3 className="text-2xl font-serif-display text-[#2C2825] mb-2">
            Choose Your Guest
          </h3>
          <p className="text-stone-500">
            Select a guest scenario to practice with. Each has different challenges and objections.
          </p>
        </div>

        <div className="space-y-6">
          {(['high_regard', 'medium_regard', 'low_regard', 'no_regard'] as Difficulty[]).map((difficulty) => {
            const group = groupedPersonas[difficulty];
            if (group.length === 0) return null;

            const colors = DIFFICULTY_COLORS[difficulty];

            return (
              <div key={difficulty}>
                <div className="flex items-center gap-2 mb-3">
                  <span
                    className={`px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider ${colors.bg} ${colors.text}`}
                  >
                    {colors.label}
                  </span>
                  <span className="text-xs text-stone-400">
                    {group.length} scenario{group.length !== 1 ? 's' : ''}
                  </span>
                </div>

                <div className="space-y-3">
                  {group.map((persona) => {
                    // Hide details for low/no regard OR if name is missing (evaluation mode)
                    const hideDetails =
                      difficulty === 'low_regard' ||
                      difficulty === 'no_regard' ||
                      !persona.name;

                    return (
                      <button
                        key={persona.id}
                        onClick={() => onSelect(persona)}
                        className="w-full text-left bg-white/80 backdrop-blur-sm rounded-xl p-5 border border-stone-200 hover:border-stone-300 hover:shadow-lg transition-all group"
                      >
                        <div className="flex items-start gap-4">
                          <div className="flex-1 min-w-0">
                            {hideDetails ? (
                              <>
                                <p className="text-sm text-stone-500 mb-2">
                                  {persona.backstory}
                                </p>
                              </>
                            ) : (
                              <>
                                <div className="flex items-center gap-2 mb-1">
                                  <h4 className="font-medium text-[#2C2825]">{persona.name}</h4>
                                </div>
                                <p className="text-sm text-stone-500 mb-2 line-clamp-2">
                                  {persona.backstory}
                                </p>
                              </>
                            )}
                          </div>
                          <ChevronRight className="w-5 h-5 text-stone-300 group-hover:text-stone-500 flex-shrink-0 mt-1 transition-colors" />
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-8 text-center">
          <button
            onClick={onCancel}
            className="px-6 py-2 text-stone-500 hover:text-stone-700 text-sm font-bold uppercase tracking-wider transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
};

export default PersonaSelector;
