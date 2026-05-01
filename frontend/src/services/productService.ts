import { logger } from './logger';

const API_BASE = `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/products`;

export interface ProductType {
  id: string;
  name: string;
  description: string;
}

export interface ProductCategory {
  id: string;
  name: string;
  description: string;
  types: ProductType[];
}

interface ProductCatalogResponse {
  categories: ProductCategory[];
}

/**
 * Fetch the complete product catalog (categories and types).
 */
export async function fetchProducts(): Promise<ProductCategory[]> {
  try {
    const response = await fetch(API_BASE, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch products: ${response.status}`);
    }

    const data: ProductCatalogResponse = await response.json();
    return data.categories;
  } catch (err) {
    logger.error('Network', 'Failed to fetch products', { error: err });
    throw err;
  }
}
