import React, { useEffect, useState } from 'react';
import { fetchProducts, ProductCategory } from '@/services/productService';
import { Loader2, AlertCircle, ArrowLeft } from 'lucide-react';
import { AT } from '@/styles/tokens';

interface ProductSelectorProps {
  onSelect: (categoryId: string, typeId: string | null) => void;
  onSkip: () => void;
  onBack: () => void;
}

function CategoryRow({ category, onSelect }: { category: ProductCategory; onSelect: (id: string, typeId: string | null) => void }) {
  const [hovered, setHovered] = useState(false);
  return (
    <button
      onClick={() => onSelect(category.id, null)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        textAlign: 'left', width: '100%',
        background: AT.surface,
        border: `1px solid ${hovered ? AT.terra + '60' : AT.hair}`,
        borderRadius: 12, padding: '16px 18px',
        cursor: 'pointer',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        transition: 'border-color 0.15s',
      }}
    >
      <div>
        <div style={{ fontFamily: AT.display, fontSize: 16, fontWeight: 600, color: AT.ink, marginBottom: 4 }}>
          {category.name}
        </div>
        <div style={{ fontSize: 13, color: AT.inkSoft }}>{category.description}</div>
      </div>
      <div style={{ fontFamily: AT.mono, fontSize: 14, color: hovered ? AT.terra : AT.inkMuted, transition: 'color 0.15s', marginLeft: 16 }}>
        ›
      </div>
    </button>
  );
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
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: AT.bg }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 style={{ width: 32, height: 32, color: AT.terra, margin: '0 auto 16px', animation: 'spin 1s linear infinite' }} />
          <p style={{ fontFamily: AT.mono, fontSize: 12, color: AT.inkMuted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Loading collections...
          </p>
        </div>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: AT.bg, padding: 24 }}>
        <div style={{ textAlign: 'center', maxWidth: 400 }}>
          <AlertCircle style={{ width: 48, height: 48, color: AT.terra, margin: '0 auto 16px' }} />
          <h3 style={{ fontFamily: AT.display, fontSize: 22, fontWeight: 600, color: AT.ink, marginBottom: 8 }}>
            Unable to Load Collections
          </h3>
          <p style={{ color: AT.inkSoft, fontSize: 14, marginBottom: 24 }}>{error}</p>
          <button
            onClick={onBack}
            style={{
              padding: '10px 24px', borderRadius: 8,
              background: AT.surface2, color: AT.ink,
              border: `1px solid ${AT.hair}`,
              fontFamily: AT.mono, fontSize: 12,
              letterSpacing: '0.1em', cursor: 'pointer',
            }}
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, overflow: 'auto', background: AT.bg, padding: '28px 40px 48px' }}>
      <div style={{ maxWidth: 640, margin: '0 auto' }}>
        <div style={{ marginBottom: 28 }}>
          <div style={{ fontFamily: AT.display, fontSize: 36, fontWeight: 600, letterSpacing: '-0.02em', color: AT.ink, lineHeight: 1 }}>
            Choose a <span style={{ color: AT.terra, fontStyle: 'italic' }}>collection</span>
          </div>
          <div style={{ marginTop: 10, fontSize: 14, color: AT.inkSoft, lineHeight: 1.5 }}>
            Focus the conversation on a specific product, or skip to practice any scenario.
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {categories.map((category: ProductCategory) => (
            <CategoryRow key={category.id} category={category} onSelect={onSelect} />
          ))}
        </div>

        <div style={{ marginTop: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
          <button
            onClick={onBack}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              background: 'none', border: 'none',
              fontFamily: AT.mono, fontSize: 11,
              color: AT.inkMuted, letterSpacing: '0.12em',
              textTransform: 'uppercase', cursor: 'pointer',
            }}
          >
            <ArrowLeft size={12} /> Back
          </button>
          <button
            onClick={onSkip}
            style={{
              padding: '8px 20px', borderRadius: 8,
              background: AT.surface2, color: AT.inkSoft,
              border: `1px solid ${AT.hair}`,
              fontFamily: AT.mono, fontSize: 11,
              letterSpacing: '0.12em', textTransform: 'uppercase',
              cursor: 'pointer',
            }}
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductSelector;
