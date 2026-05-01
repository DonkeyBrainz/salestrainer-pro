import React, { useEffect, useState } from 'react';
import { fetchProducts, ProductCategory } from '@/services/productService';
import { Loader2, AlertCircle, ChevronRight, ArrowLeft } from 'lucide-react';

interface ProductSelectorProps {
  onSelect: (categoryId: string, typeId: string | null) => void;
  onSkip: () => void;
  onBack: () => void;
}

const ProductSelector: React.FC<ProductSelectorProps> = ({ onSelect, onSkip, onBack }) => {
  const [categories, setCategories] = useState<ProductCategory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadProducts = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await fetchProducts();
        setCategories(data);
      } catch {
        setError('Failed to load product catalog');
      } finally {
        setIsLoading(false);
      }
    };

    loadProducts();
  }, []);

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 text-[#8B5E3C] animate-spin mx-auto mb-4" />
          <p className="text-stone-500">Loading collections...</p>
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
            Unable to Load Collections
          </h3>
          <p className="text-stone-500 mb-6">{error}</p>
          <button
            onClick={onBack}
            className="px-6 py-2 bg-stone-200 hover:bg-stone-300 rounded-full text-sm font-bold uppercase tracking-wider text-stone-600 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8">
      <div className="max-w-2xl mx-auto">
        <div className="text-center mb-8">
          <h3 className="text-2xl font-serif-display text-[#2C2825] mb-2">
            Choose a Collection
          </h3>
          <p className="text-stone-500">
            Select a product collection to focus the conversation, or skip to practice without a specific product.
          </p>
        </div>

        <div className="space-y-3">
          {categories.map((category) => (
            <button
              key={category.id}
              onClick={() => onSelect(category.id, null)}
              className="w-full text-left bg-white/80 backdrop-blur-sm rounded-xl p-5 border border-stone-200 hover:border-stone-300 hover:shadow-lg transition-all group"
            >
              <div className="flex items-center gap-4">
                <div className="flex-1 min-w-0">
                  <h4 className="font-medium text-[#2C2825] mb-1">{category.name}</h4>
                  <p className="text-sm text-stone-500">{category.description}</p>
                </div>
                <ChevronRight className="w-5 h-5 text-stone-300 group-hover:text-stone-500 flex-shrink-0 transition-colors" />
              </div>
            </button>
          ))}
        </div>

        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            onClick={onBack}
            className="flex items-center gap-1 px-6 py-2 text-stone-500 hover:text-stone-700 text-sm font-bold uppercase tracking-wider transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back
          </button>
          <button
            onClick={onSkip}
            className="px-6 py-2 bg-stone-200 hover:bg-stone-300 rounded-full text-sm font-bold uppercase tracking-wider text-stone-600 transition-colors"
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductSelector;
