import { Persona } from '@/types';
import { logger } from './logger';

const API_BASE = `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/personas`;

interface PersonaListResponse {
  personas: Persona[];
}

/**
 * Fetch all available personas for training mode.
 */
export async function fetchPersonas(): Promise<Persona[]> {
  try {
    const response = await fetch(API_BASE, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch personas: ${response.status}`);
    }

    const data: PersonaListResponse = await response.json();
    return data.personas;
  } catch (err) {
    logger.error('Network', 'Failed to fetch personas', { error: err });
    throw err;
  }
}

/**
 * Fetch personas available for evaluation mode.
 * Note: Evaluation personas don't include name or looking_for to avoid giving unfair information.
 */
export async function fetchEvaluationPersonas(): Promise<Persona[]> {
  try {
    const response = await fetch(`${API_BASE}/evaluation`, {
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Failed to fetch evaluation personas: ${response.status}`);
    }

    const data: PersonaListResponse = await response.json();
    return data.personas;
  } catch (err) {
    logger.error('Network', 'Failed to fetch evaluation personas', { error: err });
    throw err;
  }
}

/**
 * Pick a random persona from a list.
 */
export function pickRandomPersona(personas: Persona[]): Persona | null {
  if (personas.length === 0) return null;
  const index = Math.floor(Math.random() * personas.length);
  return personas[index];
}
