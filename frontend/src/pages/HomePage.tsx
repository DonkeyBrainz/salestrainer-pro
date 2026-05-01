import React from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Trophy, Dumbbell, History, ArrowRight } from 'lucide-react';
import UserMenu from '@/components/UserMenu';
import AmbientBackground from '@/components/AmbientBackground';

const HomePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex h-screen bg-[#F9F8F6] text-[#2C2825] font-sans overflow-hidden relative">
      <AmbientBackground mode={null} audioLevel={0} sentiment="neutral" />

      <div className="absolute inset-0 flex flex-col z-20 overflow-y-auto custom-scrollbar">
        <header className="px-10 py-8 flex justify-between items-start animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="bg-[#2C2825] p-2.5 rounded-lg shadow-lg">
              <LayoutDashboard className="w-6 h-6 text-[#F9F8F6]" />
            </div>
            <h1 className="text-4xl font-serif-display font-medium text-[#2C2825]">
              Luxe Sales Coach
            </h1>
          </div>
          <UserMenu />
        </header>

        <div className="flex-1 px-10 pb-10 flex flex-col justify-center">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl mx-auto w-full">
            {/* Training Card */}
            <div
              onClick={() => navigate('/training')}
              className="group bg-white/80 backdrop-blur-md rounded-2xl p-10 border border-stone-200 shadow-sm hover:shadow-2xl transition-all cursor-pointer overflow-hidden hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-[#8B5E3C] rounded-xl flex items-center justify-center mb-8 shadow-lg">
                <Dumbbell className="w-7 h-7 text-white" />
              </div>
              <h3 className="text-3xl font-serif-display text-[#2C2825] mb-4">
                Training & Drills
              </h3>
              <p className="text-stone-500 text-lg leading-relaxed mb-10">
                Guided scrimmage with real-time HUD feedback. Practice specific scenarios with AI hints and coaching interruptions.
              </p>
              <div className="flex items-center gap-2 text-[#8B5E3C] font-bold text-sm uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                Start Practice <ArrowRight className="w-5 h-5" />
              </div>
            </div>

            {/* Evaluation Card */}
            <div
              onClick={() => navigate('/evaluation')}
              className="group bg-white/80 backdrop-blur-md rounded-2xl p-10 border border-stone-200 shadow-sm hover:shadow-2xl transition-all cursor-pointer overflow-hidden hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-red-50 rounded-xl flex items-center justify-center mb-8">
                <Trophy className="w-7 h-7 text-red-500" />
              </div>
              <h3 className="text-3xl font-serif-display text-[#2C2825] mb-4">
                Final Evaluation
              </h3>
              <p className="text-stone-500 text-lg leading-relaxed mb-10">
                Strict guest scrimmage. No hints, no coaching. Provide a realistic test of your skills and receive a graded audit.
              </p>
              <div className="flex items-center gap-2 text-red-500 font-bold text-sm uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                Start Test <ArrowRight className="w-5 h-5" />
              </div>
            </div>

            {/* Session History Card */}
            <div
              onClick={() => navigate('/history')}
              className="group bg-white/80 backdrop-blur-md rounded-2xl p-10 border border-stone-200 shadow-sm hover:shadow-2xl transition-all cursor-pointer overflow-hidden hover:-translate-y-1"
            >
              <div className="w-14 h-14 bg-blue-50 rounded-xl flex items-center justify-center mb-8">
                <History className="w-7 h-7 text-blue-600" />
              </div>
              <h3 className="text-3xl font-serif-display text-[#2C2825] mb-4">
                Session History
              </h3>
              <p className="text-stone-500 text-lg leading-relaxed mb-10">
                Review past training sessions and evaluations. View transcripts and scorecard feedback.
              </p>
              <div className="flex items-center gap-2 text-blue-600 font-bold text-sm uppercase tracking-widest opacity-0 group-hover:opacity-100 transition-all">
                View History <ArrowRight className="w-5 h-5" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
